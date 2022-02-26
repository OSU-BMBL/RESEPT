import os.path as osp
import pickle
import shutil
import tempfile
import os
import mmcv
import numpy as np
import torch
import torch.distributed as dist
from mmcv.image import tensor2imgs
from mmcv.runner import get_dist_info
import pandas as pd
import json
import cv2
from PIL import Image
from sklearn.metrics.cluster import adjusted_rand_score
import shutil
from sklearn.metrics.cluster import adjusted_rand_score, adjusted_mutual_info_score, fowlkes_mallows_score, rand_score, \
    silhouette_score, calinski_harabasz_score, davies_bouldin_score
import math


def np2tmp(array, temp_file_name=None):
    """Save ndarray to local numpy file.
    Args:
        array (ndarray): Ndarray to save.
        temp_file_name (str): Numpy file name. If 'temp_file_name=None', this
            function will generate a file name with tempfile.NamedTemporaryFile
            to save ndarray. Default: None.
    Returns:
        str: The numpy file name.
    """

    if temp_file_name is None:
        temp_file_name = tempfile.NamedTemporaryFile(
            suffix='.npy', delete=False).name
    np.save(temp_file_name, array)
    return temp_file_name


def single_gpu_test(adata,
                    model,
                    data_loader,
                    label_path,
                    output_folder,
                    show=False,
                    out_dir=None,
                    efficient_test=False, k=7):
    """Test with single GPU.
    Args:
        model (nn.Module): Model to be tested.
        data_loader (utils.data.Dataloader): Pytorch data loader.
        show (bool): Whether show results during infernece. Default: False.
        out_dir (str, optional): If specified, the results will be dumped into
            the directory to save output results.
        efficient_test (bool): Whether save the results as local numpy files to
            save CPU memory during evaluation. Default: False.
    Returns:
        list: The prediction results.
    """

    model.eval()
    results = []
    MI_list = []
    name_list = []
    ARI_list = []
    AMI_list = []
    FMI_list = []
    RI_list = []
    # Silhouette_list = []
    # CHI_list = []
    # DBI_list = []
    dataset = data_loader.dataset
    prog_bar = mmcv.ProgressBar(len(dataset))
    if label_path == None:  # test
        for i, data in enumerate(data_loader):
            with torch.no_grad():
                result = model(return_loss=False, k=k, **data)

                # calculate MI

                img_name = data['img_metas'][0].data[0][0]['filename']
                # name = img_name.split('/')[-1]
                name = os.path.basename(img_name)
                name_list.append(name)
                image_test = cv2.imread(img_name)
                predict = result[0].astype(np.int32)

                if not os.path.exists(output_folder+'result_temp/'):
                    os.makedirs(output_folder+'result_temp/')
                np.savetxt(output_folder+'result_temp/'+name.split('.png')[0]+'.csv', predict, delimiter=',')

                MI = cluster_heterogeneity(image_test, predict, 0)
                MI_list.append(MI)
            if show or out_dir:
                # print(out_dir)
                img_tensor = data['img'][0]
                img_metas = data['img_metas'][0].data[0]
                imgs = tensor2imgs(img_tensor, **img_metas[0]['img_norm_cfg'])
                assert len(imgs) == len(img_metas)
                # print(imgs)
                # print(imgs)
                for img, img_meta in zip(imgs, img_metas):
                    h, w, _ = img_meta['img_shape']
                    img_show = img[:h, :w, :]

                    ori_h, ori_w = img_meta['ori_shape'][:-1]
                    img_show = mmcv.imresize(img_show, (ori_w, ori_h))

                    if out_dir:
                        out_file = osp.join(out_dir, img_meta['ori_filename'])
                    else:
                        out_file = None

                    model.module.show_result(
                        img_show,
                        result,
                        palette=dataset.PALETTE,
                        show=show,
                        out_file=out_file)

            if isinstance(result, list):
                if efficient_test:
                    result = [np2tmp(_) for _ in result]
                results.extend(result)
            else:
                if efficient_test:
                    result = np2tmp(result)
                results.append(result)

            batch_size = data['img'][0].size(0)
            for _ in range(batch_size):
                prog_bar.update()

        MI_result = {
            'name': name_list,
            # "ARI":ARI_list,
            'MI': MI_list,
        }
        MI_result = pd.DataFrame(MI_result)
        MI_result = MI_result.sort_values(by=['MI'], ascending=False)
        # if not os.path.exists('segmentation/QA_result/'):
        #     os.makedirs('segmentation/QA_result/')

        if len(name_list) > 5:
            MI_result_top5 = MI_result[0:5]
            # print(MI_result_top5)
            name = MI_result_top5.iloc[:, 0].values
            for n in name:
                prefix = n.split('.png')[0]
                show = cv2.imread(out_dir + n)
                if not os.path.exists(output_folder + 'segmentation_map/'):
                    os.makedirs(output_folder + 'segmentation_map/')
                cv2.imwrite(output_folder + 'segmentation_map/' + n, show)

                if not os.path.exists(output_folder+'result/'):
                    os.makedirs(output_folder+'result/')
                shutil.move(output_folder+'result_temp/'+prefix+'.csv', output_folder+'result/'+prefix+'.csv')
                category_map = pd.read_csv(output_folder+'result/'+prefix+'.csv',header =None)
                get_spot_category(adata, category_map, 'vote',prefix)

            shutil.rmtree(out_dir)
            shutil.rmtree(output_folder+'result_temp/')
            adata.obs.to_csv(output_folder + 'predicted_tissue_architecture.csv')
            # print(name)
            MI_result_top5.to_csv(output_folder + 'top5_MI_value.csv', index=True, header=True)
        else:
            name = MI_result.iloc[:, 0].values
            for n in name:
                prefix = n.split('.png')[0]
                show = cv2.imread(out_dir + n)
                if not os.path.exists(output_folder + 'segmentation_map/'):
                    os.makedirs(output_folder + 'segmentation_map/')
                cv2.imwrite(output_folder + 'segmentation_map/' + n, show)

                if not os.path.exists(output_folder + 'result/'):
                    os.makedirs(output_folder + 'result/')
                shutil.move(output_folder + 'result_temp/' + prefix + '.csv', output_folder + 'result/' + prefix + '.csv')
                category_map = pd.read_csv(output_folder+'result/'+prefix+'.csv',header =None)
                get_spot_category(adata, category_map, 'vote',prefix)

            shutil.rmtree(out_dir)
            shutil.rmtree(output_folder + 'result_temp/')
            adata.obs.to_csv(output_folder + 'predicted_tissue_architecture.csv')
            MI_result.to_csv(output_folder + 'top5_MI_value.csv', index=True, header=True)

        top1_name = MI_result.iloc[:, 0].values[0]
        top1_csv_name = output_folder + 'result/' + top1_name.split('.png')[0] + '.csv'
        top1_category_map = np.loadtxt(top1_csv_name,dtype=np.int32, delimiter=",")
        shutil.rmtree(output_folder + 'result/')
        return results, top1_category_map
    else:  # evaluation
        for i, data in enumerate(data_loader):
            with torch.no_grad():
                result = model(return_loss=False, k=k, **data)

                # calculate MI

                img_name = data['img_metas'][0].data[0][0]['filename']
                name, ARI, AMI, FMI, RI = calculate(adata, result, img_name, label_path)
                name_list.append(name)
                ARI_list.append(ARI)
                AMI_list.append(AMI)
                FMI_list.append(FMI)
                RI_list.append(RI)

                image_test = cv2.imread(img_name)
                predict = result[0].astype(np.int32)


                if not os.path.exists(output_folder+'result_temp/'):
                    os.makedirs(output_folder+'result_temp/')
                np.savetxt(output_folder+'result_temp/'+name.split('.png')[0]+'.csv', predict, delimiter=',')

                MI = cluster_heterogeneity(image_test, predict, 0)
                MI_list.append(MI)
            if show or out_dir:
                # print(out_dir)
                img_tensor = data['img'][0]
                img_metas = data['img_metas'][0].data[0]
                imgs = tensor2imgs(img_tensor, **img_metas[0]['img_norm_cfg'])
                assert len(imgs) == len(img_metas)
                # print(imgs)
                # print(imgs)
                for img, img_meta in zip(imgs, img_metas):
                    h, w, _ = img_meta['img_shape']
                    img_show = img[:h, :w, :]

                    ori_h, ori_w = img_meta['ori_shape'][:-1]
                    img_show = mmcv.imresize(img_show, (ori_w, ori_h))

                    if out_dir:
                        out_file = osp.join(out_dir, img_meta['ori_filename'])
                    else:
                        out_file = None

                    model.module.show_result(
                        img_show,
                        result,
                        palette=dataset.PALETTE,
                        show=show,
                        out_file=out_file)

            if isinstance(result, list):
                if efficient_test:
                    result = [np2tmp(_) for _ in result]
                results.extend(result)
            else:
                if efficient_test:
                    result = np2tmp(result)
                results.append(result)

            batch_size = data['img'][0].size(0)
            for _ in range(batch_size):
                prog_bar.update()

        MI_result = {
            'name': name_list,
            "ARI": ARI_list,
            "AMI": AMI_list,
            "FMI": FMI_list,
            "RI": RI_list,
            'MI': MI_list,

        }
        MI_result = pd.DataFrame(MI_result)
        MI_result = MI_result.sort_values(by=['MI'], ascending=False)
        # if not os.path.exists('segmentation/QA_result/'):
        #     os.makedirs('segmentation/QA_result/')

        if len(name_list) > 5:
            MI_result_top5 = MI_result[0:5]
            name = MI_result_top5.iloc[:, 0].values
            for n in name:
                prefix = n.split('.png')[0]
                show = cv2.imread(out_dir + n)
                if not os.path.exists(output_folder + 'segmentation_map/'):
                    os.makedirs(output_folder + 'segmentation_map/')
                cv2.imwrite(output_folder + 'segmentation_map/' + n, show)

                if not os.path.exists(output_folder+'result/'):
                    os.makedirs(output_folder+'result/')
                shutil.move(output_folder+'result_temp/'+prefix+'.csv', output_folder+'result/'+prefix+'.csv')

                category_map = pd.read_csv(output_folder+'result/'+prefix+'.csv',header =None)
                get_spot_category(adata, category_map, 'vote',prefix)

            shutil.rmtree(out_dir)
            shutil.rmtree(output_folder+'result_temp/')
            shutil.rmtree(output_folder+'result/')
            # print(name)
            adata.obs.to_csv(output_folder + 'predicted_tissue_architecture.csv')
            MI_result_top5.to_csv(output_folder + 'top5_evaluation.csv', index=False, header=True)
        else:
            name = MI_result.iloc[:, 0].values
            for n in name:
                prefix = n.split('.png')[0]
                show = cv2.imread(out_dir + n)
                if not os.path.exists(output_folder + 'segmentation_map/'):
                    os.makedirs(output_folder + 'segmentation_map/')
                cv2.imwrite(output_folder + 'segmentation_map/' + n, show)

                if not os.path.exists(output_folder+'result/'):
                    os.makedirs(output_folder+'result/')
                shutil.move(output_folder+'result_temp/'+prefix+'.csv', output_folder+'result/'+prefix+'.csv')

                category_map = pd.read_csv(output_folder+'result/'+prefix+'.csv',header =None)
                get_spot_category(adata, category_map, 'vote',prefix)

            shutil.rmtree(out_dir)
            shutil.rmtree(output_folder+'result_temp/')
            shutil.rmtree(output_folder+'result/')
            adata.obs.to_csv(output_folder + 'predicted_tissue_architecture.csv')
            MI_result.to_csv(output_folder + 'top5_evaluation.csv', index=False, header=True)

        top1_name = MI_result.iloc[:, 0].values[0]
        top1_csv_name = output_folder + 'result/' + top1_name.split('.png')[0] + '.csv'

        return results, top1_csv_name




def cluster_heterogeneity(image_test, category_map, background_category):
    if len(category_map.shape) > 2:
        category_map = cv2.cvtColor(category_map, cv2.COLOR_BGR2GRAY)
    category_list = np.unique(category_map)

    # if len(image_test.shape) > 2:
    #     # image_test = cv2.cvtColor(image_test, cv2.COLOR_BGR2GRAY)
    #      image_test = cv2.imread(image_test)

    W = np.zeros((len(category_list), len(category_list)))
    for i in range(category_map.shape[0]):
        flag1 = category_map[i][0]
        flag2 = category_map[0][i]
        for j in range(category_map.shape[0]):
            if category_map[i][j] != flag1: 
                index1 = np.where(category_list == flag1)[0][0]
                index2 = np.where(category_list == category_map[i][j])[0][0]
                W[index1][index2] = 1
                W[index2][index1] = 1
                flag1 = category_map[i][j]
            if category_map[j][i] != flag2:  
                index1 = np.where(category_list == flag2)[0][0]
                index2 = np.where(category_list == category_map[j][i])[0][0]
                W[index1][index2] = 1
                W[index2][index1] = 1
                flag2 = category_map[j][i]
    W = W[1:, 1:]  #
    # print(W)
    category_num = W.shape[0]

    # print(image_test.shape)
    # print(image_test)
    # R = image_test[:,:,0]
    # G = image_test[:,:,1]

    # print(R.shape)
    MI_list = []
    image_test_ori = image_test

    for channel in range(3):
        image_test = image_test_ori[:, :, channel]
        # print(image_test)
        num = 0
        gray_list = []
        gray_mean = 0
        for category in category_list:
            pixel_x, pixel_y = np.where(category_map == category)
            if category == background_category:
                num = len(pixel_x)
                continue
            gray = []
            for i in range(len(pixel_x)):
                gray.append(image_test[pixel_x[i], pixel_y[i]])
            gray_value = np.mean(gray)
            gray_list.append(gray_value)
            gray_mean += gray_value * len(pixel_x)
        gray_mean = gray_mean / (image_test.shape[0] ** 2 - num)

        n = W.shape[0]
        a = 0
        b = 0
        for p in range(n):
            index, = np.where(W[p] == 1)
            for q in range(len(index)):
                a += abs((gray_list[p] - gray_mean) * (gray_list[index[q]] - gray_mean))
            b += (gray_list[p] - gray_mean) ** 2
        MI = n * a / (b * np.sum(W))
        MI_list.append(MI)
    # print(MI_list)
    MI = math.sqrt((MI_list[0] ** 2 + MI_list[1] ** 2 + MI_list[2] ** 2) / 3)
    # print(MI)
    return MI


def multi_gpu_test(model,
                   data_loader,
                   tmpdir=None,
                   gpu_collect=False,
                   efficient_test=False):
    """Test model with multiple gpus.
    This method tests model with multiple gpus and collects the results
    under two different modes: gpu and cpu modes. By setting 'gpu_collect=True'
    it encodes results to gpu tensors and use gpu communication for results
    collection. On cpu mode it saves the results on different gpus to 'tmpdir'
    and collects them by the rank 0 worker.
    Args:
        model (nn.Module): Model to be tested.
        data_loader (utils.data.Dataloader): Pytorch data loader.
        tmpdir (str): Path of directory to save the temporary results from
            different gpus under cpu mode.
        gpu_collect (bool): Option to use either gpu or cpu to collect results.
        efficient_test (bool): Whether save the results as local numpy files to
            save CPU memory during evaluation. Default: False.
    Returns:
        list: The prediction results.
    """

    model.eval()
    results = []
    dataset = data_loader.dataset
    rank, world_size = get_dist_info()
    if rank == 0:
        prog_bar = mmcv.ProgressBar(len(dataset))
    for i, data in enumerate(data_loader):
        with torch.no_grad():
            result = model(return_loss=False, rescale=True, **data)

        if isinstance(result, list):
            if efficient_test:
                result = [np2tmp(_) for _ in result]
            results.extend(result)
        else:
            if efficient_test:
                result = np2tmp(result)
            results.append(result)

        if rank == 0:
            batch_size = data['img'][0].size(0)
            for _ in range(batch_size * world_size):
                prog_bar.update()

    # collect results from all ranks
    if gpu_collect:
        results = collect_results_gpu(results, len(dataset))
    else:
        results = collect_results_cpu(results, len(dataset), tmpdir)
    return results


def collect_results_cpu(result_part, size, tmpdir=None):
    """Collect results with CPU."""
    rank, world_size = get_dist_info()
    # create a tmp dir if it is not specified
    if tmpdir is None:
        MAX_LEN = 512
        # 32 is whitespace
        dir_tensor = torch.full((MAX_LEN,),
                                32,
                                dtype=torch.uint8,
                                device='cuda')
        if rank == 0:
            tmpdir = tempfile.mkdtemp()
            tmpdir = torch.tensor(
                bytearray(tmpdir.encode()), dtype=torch.uint8, device='cuda')
            dir_tensor[:len(tmpdir)] = tmpdir
        dist.broadcast(dir_tensor, 0)
        tmpdir = dir_tensor.cpu().numpy().tobytes().decode().rstrip()
    else:
        mmcv.mkdir_or_exist(tmpdir)
    # dump the part result to the dir
    mmcv.dump(result_part, osp.join(tmpdir, 'part_{}.pkl'.format(rank)))
    dist.barrier()
    # collect all parts
    if rank != 0:
        return None
    else:
        # load results of all parts from tmp dir
        part_list = []
        for i in range(world_size):
            part_file = osp.join(tmpdir, 'part_{}.pkl'.format(i))
            part_list.append(mmcv.load(part_file))
        # sort the results
        ordered_results = []
        for res in zip(*part_list):
            ordered_results.extend(list(res))
        # the dataloader may pad some samples
        ordered_results = ordered_results[:size]
        # remove tmp dir
        shutil.rmtree(tmpdir)
        return ordered_results


def collect_results_gpu(result_part, size):
    """Collect results with GPU."""
    rank, world_size = get_dist_info()
    # dump result part to tensor with pickle
    part_tensor = torch.tensor(
        bytearray(pickle.dumps(result_part)), dtype=torch.uint8, device='cuda')
    # gather all result part tensor shape
    shape_tensor = torch.tensor(part_tensor.shape, device='cuda')
    shape_list = [shape_tensor.clone() for _ in range(world_size)]
    dist.all_gather(shape_list, shape_tensor)
    # padding result part tensor to max length
    shape_max = torch.tensor(shape_list).max()
    part_send = torch.zeros(shape_max, dtype=torch.uint8, device='cuda')
    part_send[:shape_tensor[0]] = part_tensor
    part_recv_list = [
        part_tensor.new_zeros(shape_max) for _ in range(world_size)
    ]
    # gather all result part
    dist.all_gather(part_recv_list, part_send)

    if rank == 0:
        part_list = []
        for recv, shape in zip(part_recv_list, shape_list):
            part_list.append(
                pickle.loads(recv[:shape[0]].cpu().numpy().tobytes()))
        # sort the results
        ordered_results = []
        for res in zip(*part_list):
            ordered_results.extend(list(res))
        # the dataloader may pad some samples
        ordered_results = ordered_results[:size]
        return ordered_results


def calculate(adata, output, img_path, label_path):
    img_name = os.path.basename(img_path)
    samples_num = img_name.split('_')[0]  # eg:151507

    labels = save_spot_RGB_to_image(label_path, adata)  # label

    label = labels.flatten().tolist()
    output = np.array(output).flatten().tolist()
    # print('len(output)',len(output))

    label_final = []
    output_final = []
    shape = adata.uns["img_shape"]
    for i in range(shape ** 2):
        if label[i] != 0:
            label_final.append(label[i])
            output_final.append(output[i])


    ARI = adjusted_rand_score(label_final, output_final)
    AMI = adjusted_mutual_info_score(label_final, output_final)
    FMI = fowlkes_mallows_score(label_final, output_final)
    RI = rand_score(label_final, output_final)
    print('name', img_name)

    print('ARI:', ARI)

    return img_name, ARI, AMI, FMI, RI


def save_spot_RGB_to_image(label_path, adata):
    # data_file = os.path.join(data_folder, expression_file)
    X = pd.read_csv(label_path)
    X = X.sort_values(by=['barcode'])
    # print(X)
    # print(adata.obs)
    assert all(adata.obs.index == X.iloc[:, 0].values)
    layers = X.iloc[:, 1].values
    # print(layers)
    spot_row = adata.obs["pxl_col_in_fullres"]
    spot_col = adata.obs["pxl_row_in_fullres"]

    radius = int(0.5 * adata.uns['fiducial_diameter_fullres'] + 1)
    # radius = int(scaler['spot_diameter_fullres'] + 1)
    max_row = max_col = int((2000 / adata.uns['tissue_hires_scalef']) + 1)
    # radius = round(radius * (600 / 2000))

    # max_row = np.max(spot_row)
    # max_col = np.max(spot_col)

    img = np.zeros(shape=(max_row + 1, max_col + 1), dtype=np.int)

    img = img.astype(np.uint8)
    for index in range(len(layers)):
        if layers[index] == 'Layer1':
            # print('layer1')
            # img[spot_row[index], spot_col[index]] = [0,0,255]
            img[(spot_row[index] - radius):(spot_row[index] + radius),
            (spot_col[index] - radius):(spot_col[index] + radius)] = 1
            # print(img[spot_row[index],spot_col[index]])
            # cv2.circle(img,(spot_row[index], spot_col[index]),radius,(0,0,255),thickness=-1)
        elif layers[index] == 'Layer2':
            img[(spot_row[index] - radius):(spot_row[index] + radius),
            (spot_col[index] - radius):(spot_col[index] + radius)] = 2
            # img[spot_row[index], spot_col[index]] = [0,255,0]
            # cv2.circle(img,(spot_row[index], spot_col[index]),radius,(0,255,0),thickness=-1)
            # print(img[spot_row[index],spot_col[index]])
        elif layers[index] == 'Layer3':
            img[(spot_row[index] - radius):(spot_row[index] + radius),
            (spot_col[index] - radius):(spot_col[index] + radius)] = 3
            # img[spot_row[index], spot_col[index]] = [255,0,0]
            # cv2.circle(img,(spot_row[index], spot_col[index]),radius,(255,0,0),thickness=-1)
        elif layers[index] == 'Layer4':
            img[(spot_row[index] - radius):(spot_row[index] + radius),
            (spot_col[index] - radius):(spot_col[index] + radius)] = 4
            # img[spot_row[index], spot_col[index]] = [255,0,255]
            # cv2.circle(img,(spot_row[index], spot_col[index]),radius,(255,0,255),thickness=-1)
        elif layers[index] == 'Layer5':
            img[(spot_row[index] - radius):(spot_row[index] + radius),
            (spot_col[index] - radius):(spot_col[index] + radius)] = 5
            # img[spot_row[index], spot_col[index]] = [0,255,255]
            # cv2.circle(img,(spot_row[index], spot_col[index]),radius,(0,255,255),thickness=-1)
        elif layers[index] == 'Layer6':
            img[(spot_row[index] - radius):(spot_row[index] + radius),
            (spot_col[index] - radius):(spot_col[index] + radius)] = 6
            # img[spot_row[index], spot_col[index]] = [255,255,0]
            # cv2.circle(img,(spot_row[index], spot_col[index]),radius,(255,255,0),thickness=-1)
        elif layers[index] == 'WM':
            img[(spot_row[index] - radius):(spot_row[index] + radius),
            (spot_col[index] - radius):(spot_col[index] + radius)] = 7
            # img[spot_row[index], spot_col[index]] = [0,0,0]
            # cv2.circle(img,(spot_row[index], spot_col[index]),radius,(0,0,0),thickness=-1)

    shape = adata.uns["img_shape"]
    label_img = cv2.resize(img, dsize=(shape, shape), interpolation=cv2.INTER_NEAREST)
    return label_img


def single_gpu_train_pipeline(model,
                    data_loader,
                    show=False,
                    out_dir=None,
                    efficient_test=False):
    """Test with single GPU.

    Args:
        model (nn.Module): Model to be tested.
        data_loader (utils.data.Dataloader): Pytorch data loader.
        show (bool): Whether show results during infernece. Default: False.
        out_dir (str, optional): If specified, the results will be dumped into
            the directory to save output results.
        efficient_test (bool): Whether save the results as local numpy files to
            save CPU memory during evaluation. Default: False.

    Returns:
        list: The prediction results.
    """

    model.eval()
    results = []
    ARI_list = []
    MI_list = []
    name_list = []  
    ARI_dic = {}
    MI_dic = {}
    # epoch_list = {}

    dataset = data_loader.dataset
    prog_bar = mmcv.ProgressBar(len(dataset))
    for i, data in enumerate(data_loader):
        with torch.no_grad():
            result = model(return_loss=False, **data)

            #calculate ARI

            img_name = data['img_metas'][0].data[0][0]['filename']
            # name = img_name.split('/')[-1]
            name = os.path.basename(img_name)
            
            # name, ARI = calculate(result,img_name)
            name_list.append(img_name)
            # ARI_list.append(ARI)
            # ARI_dic[name] = ARI
            image_test = cv2.imread(img_name)
            predict = result[0].astype(np.uint8)
            num = name.split('_')[0]
            norm = name.split('_')[1]
            MI = cluster_heterogeneity(image_test, predict, 0)
            MI_list.append(MI)
            MI_dic[name] = MI
        if show or out_dir:
            img_tensor = data['img'][0]
            img_metas = data['img_metas'][0].data[0]
            imgs = tensor2imgs(img_tensor, **img_metas[0]['img_norm_cfg'])
            assert len(imgs) == len(img_metas)

            for img, img_meta in zip(imgs, img_metas):
                h, w, _ = img_meta['img_shape']
                img_show = img[:h, :w, :]

                ori_h, ori_w = img_meta['ori_shape'][:-1]
                img_show = mmcv.imresize(img_show, (ori_w, ori_h))

                if out_dir:
                    out_file = osp.join(out_dir, img_meta['ori_filename'])
                else:
                    out_file = None

                model.module.show_result(
                    img_show,
                    result,
                    palette=dataset.PALETTE,
                    show=show,
                    out_file=out_file)

        if isinstance(result, list):
            if efficient_test:
                result = [np2tmp(_) for _ in result]
            results.extend(result)
        else:
            if efficient_test:
                result = np2tmp(result)
            results.append(result)

        batch_size = data['img'][0].size(0)
        for _ in range(batch_size):
            prog_bar.update()

    ARI_result = {
                  'name':name_list,
                  # "ARI":ARI_list,
                  'MI':MI_list,
                  }
    ARI_result = pd.DataFrame(ARI_result)
    ARI_result = ARI_result.sort_values(by=['MI'], ascending=False)
    ARI_result.to_csv('./train_pipeline_test'+'.csv',index=False, header=False,mode='a')

    return results

def get_spot_category_by_center_pixel(category_map, center_x, center_y):

    return category_map[center_x, center_y]

def get_spot_category_by_pixel_vote(category_map, center_x, center_y,max_row, max_col, radius):

    spot_region_start_x = center_x - radius
    spot_region_end_x = center_x + radius
    spot_region_start_y = center_y - radius
    spot_region_end_y = center_y + radius

    if spot_region_start_x < 0:
        spot_region_start_x = 0
    if spot_region_start_y < 0:
        spot_region_start_y = 0
    if spot_region_end_x > max_row:
        spot_region_end_x = max_row
    if spot_region_end_y > max_col:
        spot_region_end_y = max_col

    spot_region = category_map.values[spot_region_start_x:  spot_region_end_x,spot_region_start_y: spot_region_end_y]
    # print(spot_region)
    categories, votes = np.unique(spot_region, return_counts=True)

    return int(categories[np.argmax(votes)])

def get_spot_category(adata, category_map, strategy,name):
    predict = []
    #infer resolution
    if category_map.shape[0] == 600:
        # low resolution
        resolution = 'low'
        radius = int((0.5 * adata.uns['fiducial_diameter_fullres'] + 1) * adata.uns['tissue_lowres_scalef'])
        max_row = max_col = 600
    elif category_map.shape[0] == 400:
        # low resolution
        resolution = 'low'
        radius = int((0.5 * adata.uns['fiducial_diameter_fullres'] + 1) * adata.uns['tissue_lowres_scalef'])
        max_row = 400
        max_col = 600
    elif category_map.shape[0] == 2000:
        #high resolution
        resolution = 'high'
        radius = int((0.5 * adata.uns['fiducial_diameter_fullres'] + 1) * adata.uns['tissue_hires_scalef'])
        max_row = max_col = 2000
    else:
        #full resolution
        resolution = 'full'
        radius = int(0.5 * adata.uns['fiducial_diameter_fullres'] + 1)
        max_row = max_col = int((2000 / adata.uns['tissue_hires_scalef']) + 1)
    for index, row in adata.obs.iterrows():
        if resolution == 'low':
            center_x = int((row['pxl_col_in_fullres'] /(2000 / adata.uns['tissue_hires_scalef'] + 1)) *600)
            center_y = int((row['pxl_row_in_fullres'] /(2000 / adata.uns['tissue_hires_scalef'] + 1)) *600)
            # print(center_x, center_y)
        elif resolution == 'high':
            center_x = int((row['pxl_col_in_fullres'] /(2000 / adata.uns['tissue_hires_scalef'] + 1)) *2000)
            center_y = int((row['pxl_row_in_fullres'] /(2000 / adata.uns['tissue_hires_scalef'] + 1)) *2000)
        else:
            center_x = row['pxl_col_in_fullres']
            center_y = row['pxl_row_in_fullres']


        if strategy == 'vote':
            predictive_layer = get_spot_category_by_pixel_vote(category_map,
                                                                      center_x, center_y, max_row,
                                                                      max_col,radius)
            # row[col_name] = predictive_layer
            predict.append(predictive_layer)
        else:
            predictive_layer = get_spot_category_by_center_pixel(category_map,
                                                                        center_x, center_y)
            predict.append(predictive_layer)
    col_name = 'predicted_category_'+name
    adata.obs[col_name] = predict
