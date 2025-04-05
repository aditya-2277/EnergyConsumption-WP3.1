FROM python:3.13-slim

ADD training_service.py requirements.txt energy_databroker_pb2.py energy_databroker_pb2_grpc.py train_model_pb2.py train_model_pb2_grpc.py ./

RUN pip install --upgrade pip

RUN pip install pandas joblib scikit-learn

RUN pip install -r requirements.txt

EXPOSE 8061 8062 8063 8064

CMD ["python", "training_service.py"]