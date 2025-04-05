import grpc
from concurrent import futures

import joblib
import time

import predict_energy_pb2
import predict_energy_pb2_grpc

class PredictServicer(predict_energy_pb2_grpc.PredictServicer):
    def predictconsumption(self, request, context):
        try:
            model = joblib.load("../data/model.pkl")
            buildingType = 1
            dayOfWeek = 1
            if request.BuildingType == "Residential":
                buildingType = 1
            elif request.BuildingType == "Commercial":
                buildingType = 2
            elif request.BuildingType == "Industrial":
                buildingType = 3

            if request.DayofWeek == "Weekday":
                dayOfWeek = 1
            elif request.DayofWeek == "Weekend":
                dayOfWeek = 2

            inputFeatures = [[buildingType, request.SquareFootage, request.NumberofOccupants, request.AppliancesUsed, request.AverageTemperature, dayOfWeek]]
            prediction = model.predict(inputFeatures)[0]
            return predict_energy_pb2.Prediction(EnergyConsumption = prediction)

        except Exception as e:
            print(str(e))
            return predict_energy_pb2.Prediction(EnergyConsumption = -1)

def serve():
    port = "8063"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    predict_energy_pb2_grpc.add_PredictServicer_to_server(PredictServicer(),server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Prediction Service is running on port: " + port)
    server.wait_for_termination()

if __name__ == "__main__":
    serve()