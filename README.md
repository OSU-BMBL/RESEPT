# Define and visualize pathological architectures of human tissues from spatially resolved transcriptomics using deep learning
<img src="https://img.shields.io/badge/RESEPT-v1.0.0-green"> <img src="https://img.shields.io/badge/Platform-Linux-green"> <img src="https://img.shields.io/badge/Language-python3-green"> <img src="https://img.shields.io/badge/License-MIT-green">

```RESEPT``` is a deep-learning framework for characterizing and visualizing tissue architecture from spatially resolved transcriptomics. 

Given inputs as gene expression or RNA velocity, ```RESEPT``` learns a three-dimensional embedding with a spatial retained graph neural network from the spatial transcriptomics. The embedding is then visualized by mapping as color channels in an RGB image and segmented with a supervised convolutional neural network model for inferring the tissue architecture accurately. 


<p align="center">
  <img height="300" width="700" src="https://github.com/yuyang-0825/image/blob/main/figure1.png" />
</p>

Documentation: https://resept.readthedocs.io/

 
## System Requirements

### Hardware Requirements
 
``` RESEPT ``` was trained on a workstation with a 64-core CPU, 20G RAM, and a GPU with 11G VRAM. The function of customizing the segmentation model only can run on GPU device now. Other functions for RESEPT need the minimum requirements of a CPU with 8 cores and 8G RAM. 

### Software Requirements

#### OS Requirements
``` RESEPT ``` can run on Linux. The package has been tested on the following systems:
* Linux: Ubuntu 20.04

#### Python Dependencies
``` RESEPT ``` mainly depends on the Python (3.6+) scientific stack.
``` 
scipy==1.6.2
networkx==2.5.1
opencv_contrib_python==4.5.1.48
tqdm==4.60.0
scikit_image==0.18.1
numpy==1.19.2
umap_learn==0.5.1
six==1.15.0
matplotlib==3.3.4
terminaltables==3.1.0
torch==1.5.0
scanpy==1.7.2
statsmodels==0.12.2
requests==2.25.1
munkres==1.1.4
mmcv_full==1.3.0
rpy2==3.1.0
pandas==1.2.3
numba==0.53.1
seaborn==0.11.1
anndata==0.7.6
cityscapesscripts==2.2.0
leidenalg==0.8.7
Pillow==8.3.1
python_igraph==0.9.6
scikit_learn==0.24.2
umap==0.1.1
```
## Installation Guide

### Install dependency packages
1. Install ```PyTorch 1.5.0``` following the [official guide](https://pytorch.org/get-started/previous-versions/#linux-and-windows-9).
2. Install ```mmcv-full 1.3.0``` by running the following command:
    ```
    pip install mmcv-full==1.3.0 -f https://download.openmmlab.com/mmcv/dist/${CUDA}/torch1.5.0/index.html
    ```
    where ${CUDA} should be replaced by the specific CUDA version (cpu, cu92, cu101, cu102).

3. Install other dependencies:
    ```
    pip install -r requirements.txt
    ```
The above steps take 20-25 mins to install all dependencies.

### Install RESEPT from GitHub
```
git clone https://github.com/OSU-BMBL/RESEPT
cd RESEPT
```

## Data preparation

### 10x Visium data
 * gene expression file: A HDF5 file stores raw gene expression data.  
 * tissue_positions_list file: A csv file contains meta information of spots including their connectivity and spatial coordinates.
 * scalefactors_json file: A json file collects the scaling factors converting spots to different resolutions.  
 
 More details can be found [here](https://support.10xgenomics.com/spatial-gene-expression/software/pipelines/latest/using/count).

### Annotation file (optional)

An annotation file should include spot barcodes and their corresponding annotations. It is used for evaluating predictive tissue architectures (e.g., ARI) and training user's segmentation models. The file should be named as:[sample_name]_annotation.csv. [[example]](https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/151670_annotation.csv)

### Segmentation model file (optinal)

It is a pre-trained segmentation model file in the [pth](https://filext.com/file-extension/PTH) format, which should be provided in predicting the tissue architecture on the generative images.

### Data structure

The data schema to run our code is as follows:
```
[sample_name]/
 |__spatial/
 |    |__tissue_positions_list file
 |    |__scalefactors_json file
 |__gene expression file
 |__annotation file: [sample_name]_annotation.csv (optional)

model/ (optional)
 |__segmentation model file 
   ```
The data schema to customize our segmentation model is as follows:
```
[training_data_folder]
|__[sample_name_1]/
|    |__spatial/
|    |    |__tissue_positions_list file
|    |    |__scalefactors_json file|
|    |__gene expression file
|    |__annotation file: [sample_name_1]_annotation.csv
|__[sample_name_2]/
|    |__spatial/
|    |    |__tissue_positions_list file
|    |    |__scalefactors_json file|
|    |__gene expression file
|    |__annotation file: [sample_name_2]_annotation.csv
|    ...
|__[sample_name_n]/
|    |__spatial/
|    |    |__tissue_positions_list file
|    |    |__scalefactors_json file|
|    |__gene expression file
|    |__annotation file: [sample_name_n]_annotation.csv 
```


## Demo

### Function 1: visualize tissue architecture 
Run the following command line to construct RGB images based on gene expression from different embedding parameters. For demonstration, please download the example data from [here](https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/151669.zip) and put the unzip folder '151669' in the source code folder.
```
wget https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/151669.zip 
unzip 151669.zip
python RGB_images_pipeline.py -expression 151669/151669_filtered_feature_bc_matrix.h5  -meta 151669/spatial/tissue_positions_list.csv  -scaler 151669/spatial/scalefactors_json.json -output Demo_result  -embedding scGNN  -transform logcpm 
```

#### Command Line Arguments:
*	-expression file path for raw gene expression data. [type: str]
*	-meta file path for spatial meta data recording tissue positions. [type: str]
*	-scaler file path for scale factors. [type: str]
*	-output output root folder. [type: str]
*	-embedding embedding method in use: scGNN, spaGCN, UMAP or SEDR. [type: str] [default: scGNN]
*	-transform data pre-transform method: log, logcpm or None. [type: str] [default: logcpm]


#### Results
 ```RESEPT``` stores the generative results in the following structure:
   ```
      Demo_result/
      |__RGB_images/
   ```
*	The folder 'RGB_images' stores generated RGB images of tissue architectures from different embedding parameters.  

This demo takes 25-30 mins to generate all results on the machine with a 64-core CPU.

### Function 2: evaluate predictive tissue architectures with annotation
Run the following command line to construct RGB images based on gene expression from different embedding parameters, segment the constructed RGB images to tissue architectures with top-5 Moran's I, and evaluate the tissue architectures (e.g., ARI). For demonstration, please download the example data from [here](https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/151669.zip) and the pretrained model from [here](https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/model_151669.zip). Then put unzip folders '151669' and 'model_151669' in the source code folder.
```
wget https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/151669.zip 
wget https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/model_151669.zip
unzip 151669.zip
unzip model_151669.zip
python evaluation_pipeline.py -expression 151669/151669_filtered_feature_bc_matrix.h5  -meta 151669/spatial/tissue_positions_list.csv  -scaler 151669/spatial/scalefactors_json.json -k 7 -label 151669/151669_annotation.csv -model model_151669/151669_scGNN.pth -output Demo_result_evaluation  -embedding scGNN  -transform logcpm  -device cpu
```

#### Command Line Arguments:
*	-expression file path for raw gene expression data. [type: str]
*	-meta file path for spatial meta data recording tissue positions. [type: str]
*	-scaler file path for scale factors. [type: str]
*	-k the number of tissue architectures(setting -1 will recommend a K for you). [type: int] [default: 7]
*	-label file path for labels recording spot barcodes and their annotations for calculating evaluation metrics. [type: str]
*	-model file path for pre-trained model. [type: str]
*	-output output root folder. [type: str]
*	-embedding embedding method in use: scGNN, spaGCN, UMAP or SEDR. [type: str] [default: scGNN]
*	-transform data pre-transform method: log, logcpm or None. [type: str] [default: logcpm]
*	-device cpu/gpu device option: cpu or gpu. [type: str] [default: cpu]


#### Results
 ```RESEPT``` stores the generated results in the following structure:
   ```
      Demo_result_evaluation/
      |__RGB_images/
      |__segmentation_evaluation/
            |__segmentation_map/
            |__top5_evaluation.csv
   ```
*	The folder 'RGB_images' contains the generated RGB images of tissue architectures from different embedding parameters.
*	The folder 'segmentation_map' stores the predicted tissue architectures with top-5 Moran's I.
*	The file 'top5_evaluation.csv' records various evaluation metrics corresponding to the tissue architectures.  

This demo takes 30-35 mins to generate all results on the machine with a 64-core CPU.

### Function 3: predict tissue architecture without annotation
Run the following command line to generate RGB images based on gene expression from different embedding parameters and predict tissue architectures with top-5 Moran's I. For demonstration, please download the example data from [here](https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/151669.zip) and the pre-trained model from [here](https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/model_151669.zip). Then put unzip folders '151669' and 'model_151669' in the source code folder.
```
wget https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/151669.zip 
wget https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/model_151669.zip 
unzip model_151669.zip
unzip 151669.zip
python test_pipeline.py -expression 151669/151669_filtered_feature_bc_matrix.h5  -meta 151669/spatial/tissue_positions_list.csv  -scaler 151669/spatial/scalefactors_json.json -k 7 -model model_151669/151669_scGNN.pth -output Demo_result_tissue_architecture  -embedding scGNN  -transform logcpm -device cpu
```

#### Command Line Arguments:
*	-expression file path for raw gene expression data. [type: str]
*	-meta file path for spatial meta data recording tissue positions. [type: str]
*	-scaler file path for scale factors. [type: str]
*	-k the number of tissue architectures(setting -1 will recommend a K for you). [type: int] [default: 7]
*	-model file path for pre-trained model. [type: str]
*	-output output root folder. [type: str]
*	-embedding embedding method in use: scGNN, spaGCN, UMAP or SEDR. [type: str] [default: scGNN]
*	-transform data pre-transform method: log, logcpm or None. [type: str] [default: logcpm]
*	-device cpu/gpu device option: cpu or gpu. [type: str] [default: cpu]

#### Results
 ```RESEPT``` stores the generative results in the following structure:
   ```
   Demo_result_tissue_architecture/
   |__RGB_images/
   |__segmentation_test/
         |__segmentation_map/
         |__top5_MI_value.csv
   ```
*	The folder 'RGB_images' contains the generated RGB images of tissue architectures from different embedding parameters.
*	The folder 'segmentation_map' stores the predicted tissue architectures with top-5 Moran's I.
*	The file 'top5_MI_value.csv' records Moran's I value corresponding to the tissue architectures.  

This demo takes 30-35 mins to generate all the results on the machine with a 64-core CPU.

### Function 4: segment histological images
```RESEPT``` allows to segment a histological image according to predicted tissue architectures. It may help pathologists to focus on specific functional zonation. Run the following command line to predict tissue architectures with top-5 Moran's I and segment the histological image accordingly. For demonstration, please download the example data from [here](https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/cancer.zip) and the pre-trained model from [here](https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/model_cancer.zip). Then put unzip folders 'cancer' and 'model_cancer' in the source code folder.
```
wget https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/cancer.zip
wget https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/model_cancer.zip
unzip cancer.zip
unzip model_cancer.zip
python histological_segmentation_pipeline.py -expression ./cancer/Parent_Visium_Human_Glioblas_filtered_feature_bc_matrix.h5 -meta ./cancer/spatial/tissue_positions_list.csv -scaler ./cancer/spatial/scalefactors_json.json -k 7 -model ./model_cancer/cancer_model.pth -histological ./cancer/Parent_Visium_Human_Glioblast.tif -output Demo_result_HistoImage -embedding spaGCN -transform logcpm -device cpu
```

#### Command Line Arguments:
*	-expression file path for raw gene expression data. [type: str]
*	-meta file path for spatial meta data recording tissue positions. [type: str]
*	-scaler file path for scale factors. [type: str]
*	-k the number of tissue architectures(setting -1 will recommend a K for you). [type: int] [default: 7]
*	-model file path for pre-trained model. [type: str]
*	-histological file path for the corresponding histological image.[type: str]
*	-output output root folder. [type: str]
*	-embedding embedding method in use: scGNN, spaGCN, UMAP or SEDR. [type: str] [default: spaGCN]
*	-transform data pre-transform method: log, logcpm or None. [type: str] [default: logcpm]
*	-device cpu/gpu device option: cpu or gpu. [type: str] [default: cpu]
#### Results
 ```RESEPT``` stores the generative results in the following structure:
   ```
   Demo_result_HistoImage/
   |__RGB_images/
   |__segmentation_test/
   |     |__segmentation_map/
   |     |__top5_MI_value.csv
   |__histological_segmentation/
         |__category_1.png
         |__category_2.png
	          …
         |__category_n.png
   ```
*	The folder 'RGB_images' stores generated RGB images of tissue architectures from different embedding parameters.
*	The folder 'segmentation_map' provides predicted tissue architectures with top-5 Moran's I.
*	The file 'top5_MI_value.csv' records Moran's I value corresponding to the tissue architectures.
*	The file 'category_```n```.png' refers to the histological image segmentation results, where ```n``` denotes the segmentation number.   


This demo takes 30-35 mins to generate all results on the machine with the multi-core CPU.

### Function 5: customize segmentation model (GPU required)
 ```RESEPT``` supports fine-tuning our segmentation model by using users' 10x Visium data. Organize all samples and their annotations according to our pre-defined data schema and download our pre-trained model from [here](https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/model_151669.zip) as a training start point. Each sample for the training model should be placed in an individual folder with a specific format (the folder structure can be found [here](https://github.com/coffee19850519/single_cell_spatial_image#data-structure)). Then gather all the individual folders into one main folder (e.g., named “training_data_folder”).  For demonstration, download the example training data from [here](https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/training_data_folder.zip), and then run the following command line to generate the RGB images of your own data and customized model.
```
wget https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/model_151669.zip
wget https://bmbl.bmi.osumc.edu/downloadFiles/GitHub_files/training_data_folder.zip
unzip model_151669.zip
unzip training_data_folder.zip
python training_pipeline.py -data_folder training_data_folder -output Demo_result_model -embedding scGNN  -transform logcpm -model model_151669/151669_scGNN.pth
```

#### Command Line Arguments:
* 	-data_folder a folder provides all training samples. The data including label file of each sample should follow our pre-defined schema in a sub-folder under this folder. [type: str]
* 	-model file path for pre-trained model file. [type: str]
* 	-output output root folder. [type: str]
* 	-embedding embedding method in use: scGNN, spaGCN, UMAP or SEDR. [type: str] [default: scGNN]
* 	-transform data pre-transform method: log, logcpm or None. [type: str] [default: logcpm]

#### Results
 ```RESEPT``` stores the generative results in the following structure:
   ```
   Demo_result_model/
   |__RGB_images/
   
   work_dirs/
   |__config/
         |__fine_tune_model.pth
   ```
*	The folder 'RGB_images' contains generated RGB images of tissue architectures of all input 10x data from different embedding parameters.
*	The file 'fine_tune_model.pth' is the customized model.  

This demo takes about 3-5 hours to generate the model on the machine with 11G VRAM GPU.


## Built With
 
* [opencv](https://opencv.org/) - The image processing library used
* [pytorch](https://pytorch.org/) - The deep learning backend used
* [scikit-learn](https://scikit-learn.org/stable/) - The machine learning library used
* [mmSegmentation](https://github.com/open-mmlab/mmsegmentation) - The image segmentation library used
 
## License
 
This project is licensed under the MIT License - see the [LICENSE.md](https://github.com/coffee19850519/single_cell_spatial_image/blob/main/LICENSE) file for details
 
## Citation
if you use ```RESEPT```, please cite [our paper](https://www.biorxiv.org/content/10.1101/2021.07.08.451210v1):
```
@article {Chang2021.07.08.451210,
	author = {Chang, Yuzhou and He, Fei and Wang, Juexin and Chen, Shuo and Li, Jingyi and Liu, Jixin and Yu, Yang and Su, Li and Ma, Anjun and Allen, Carter and Lin, Yu and Sun, Shaoli and Liu, Bingqiang and Otero, Jose and Chung, Dongjun and Fu, Hongjun and Li, Zihai and Xu, Dong and Ma, Qin},
	title = {Define and visualize pathological architectures of human tissues from spatially resolved transcriptomics using deep learning},
	elocation-id = {2021.07.08.451210},
	year = {2021},
	doi = {10.1101/2021.07.08.451210},
	publisher = {Cold Spring Harbor Laboratory},
	URL = {https://www.biorxiv.org/content/early/2021/07/16/2021.07.08.451210},
	eprint = {https://www.biorxiv.org/content/early/2021/07/16/2021.07.08.451210.full.pdf},
	journal = {bioRxiv}
}
```
