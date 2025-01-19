# AI Generated Image Detection

This project trains an image classifier to detect AI generated images. The classifier is based on the research found in
this paper: [Detecting AI Generated Images](https://arxiv.org/pdf/2303.14126v1.pdf).

## CIFAKE Dataset

CIFAKE is a dataset that contains both real and AI-generated synthetic images. It is used for training machine learning
models to distinguish between real and synthetic images. The AI-generated images in the CIFAKE dataset are created using
various generative models, providing a diverse range of data for the classifier to learn from.

The dataset used for this project can be found
at [Kaggle](https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images).

Follow these steps to setup the dataset:

1. Download the dataset from the link above.
2. Unzip the downloaded file.
3. Move the unzipped files into the `./data` directory in the project root.

## Training the Model

Open the Jupyter notebook `train-model.ipynb` for instructions to train and deploy the model onto a Sagemaker Endpoint for inference.

## AWS Sagemaker

AWS Sagemaker is a fully managed service that provides developers and data scientists with the ability to build, train,
and deploy machine learning (ML) models quickly. In this project, Sagemaker is used to train the image classifier and
deploy it as a Sagemaker endpoint. The Sagemaker endpoint provides an API for making predictions with the trained model.

## Contributing

Contributions are welcome. Please submit a pull request if you have something to add or suggest.

## License

This project is licensed under the terms of the Amazon Software License.