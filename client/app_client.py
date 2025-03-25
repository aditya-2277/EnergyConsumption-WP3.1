import grpc

import energy_databroker_pb2_grpc
import energy_databroker_pb2
import train_model_pb2_grpc
import predict_energy_pb2_grpc
import predict_energy_pb2

import time

def main():
    databrokerPort = "8061"
    trainingPort = "8062"
    predictionPort = "8063"

    databroker_channel = grpc.insecure_channel("localhost:" + databrokerPort)
    training_channel = grpc.insecure_channel("localhost:" + trainingPort)
    prediction_channel = grpc.insecure_channel("localhost:" + predictionPort)

    databroker_stub = energy_databroker_pb2_grpc.DatabrokerStub(databroker_channel)
    training_stub = train_model_pb2_grpc.TrainingStub(training_channel)
    prediction_stub = predict_energy_pb2_grpc.PredictStub(prediction_channel)

    train_request = databroker_stub.energydatabroker(energy_databroker_pb2.Empty())
    print("Training File: " + train_request.csv_file_path)

    time.sleep(5)
    train_response = training_stub.trainmodel(train_request)
    print("Training Status: " + train_response.status)

    prediction_request = predict_energy_pb2.Features(BuildingType = "Residential",
                                                     SquareFootage = 24563,
                                                     NumberofOccupants = 15,
                                                     AppliancesUsed = 4,
                                                     AverageTemperature = 28.52,
                                                     DayofWeek = "Weekday"
                                                     )
    prediction_response = prediction_stub.predictconsumption(prediction_request)
    print("The predicted consumption is: " + str(prediction_response.EnergyConsumption))

if __name__ == "__main__":
    main()