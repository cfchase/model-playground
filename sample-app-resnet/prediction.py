import os
import base64
import numpy as np
import cv2
import time
import grpc
import grpc_predict_v2_pb2
import grpc_predict_v2_pb2_grpc
import classes


grpc_host = os.environ.get('GRPC_HOST', 'modelmesh-serving')
grpc_port = int(os.environ.get('GRPC_PORT', '8033'))
model_name = os.environ.get('MODEL_NAME', 'resnet')
channel = grpc.insecure_channel(f"{grpc_host}:{grpc_port}")
stub = grpc_predict_v2_pb2_grpc.GRPCInferenceServiceStub(channel)

def normalize(img_data):
    """Normalize to adjust to model training dataset
    """
    mean_vec = np.array([0.485, 0.456, 0.406])
    stddev_vec = np.array([0.229, 0.224, 0.225])
    norm_img_data = np.zeros(img_data.shape).astype('float32')
    for i in range(img_data.shape[0]):
        # for each pixel in each channel, divide the value by 255 to get value between [0, 1] and then normalize
        norm_img_data[i,:,:] = (img_data[i,:,:]/255 - mean_vec[i]) / stddev_vec[i]
    return norm_img_data


def preprocess(img_bytes, size=224):
    """Preprocess image data
    """
    img = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img, cv2.IMREAD_COLOR)  # BGR format

    # format of data is HWC
    # add image preprocessing if needed by the model
    img = cv2.resize(img, (224, 224))
    img = img.astype('float32')
    #convert to NCHW
    img = img.transpose(2,0,1)

    norm_img_data = normalize(img)
    reshaped_img_data = norm_img_data.reshape(1,3,size,size)
    return reshaped_img_data


def infer(img, size=224):
    # request content building
    inputs = []
    inputs.append(grpc_predict_v2_pb2.ModelInferRequest().InferInputTensor())
    inputs[0].name = 'gpu_0/data_0'
    inputs[0].datatype = "FP32"
    inputs[0].shape.extend([1, 3, size, size])
    arr = img.flatten()
    inputs[0].contents.fp32_contents.extend(arr)

    # request building
    request = grpc_predict_v2_pb2.ModelInferRequest()
    request.model_name = model_name
    request.inputs.extend(inputs)

    response = stub.ModelInfer(request)
    arr = np.frombuffer(response.raw_output_contents[0], dtype=np.float32)
    max = np.argmax(arr)
    class_name = classes.imagenet_classes[max]

    return class_name


def predict(body):
    base64img = body.get('image')
    img_bytes = base64.decodebytes(base64img.encode())
    data = preprocess(img_bytes)
    class_name = infer(data)
    return {'prediction': class_name}
