FROM python:3.13-slim

ADD predict_service.py requirements.txt predict_energy_pb2.py predict_energy_pb2_grpc.py ./

RUN pip install --upgrade pip

RUN pip install joblib

RUN pip install -r requirements.txt

EXPOSE 8061 8062 8063 8064

CMD ["python", "predict_service.py"]