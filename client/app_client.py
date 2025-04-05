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

    time.sleep(1)
    train_response = training_stub.trainmodel(train_request)
    print("Training Status: " + train_response.status)


    if "Error" in train_response.status:
        print("Error Occured!")
    else:
        #UserInput
        predictionReqd = input("Do you want to continue with Prediction ? Y/N : ")

    if predictionReqd == "Y":
        buildingType = input("Enter the Building Type (Residential/Commercial/Industrial) : ")
        squareFootage = float(input("Enter the Square footage (Eg. 24512) : "))
        noOfOccupants = float(input("Enter the Number of Occupants (Eg. 15) : "))
        noOfAppliances = float(input("Enter the Number of Appliances Used (Eg. 4) : "))
        avgTemp = float(input("Enter the Average temperature in C (Eg. 28.5) : "))
        dayOfWeek = input("Enter the Day of the Week (Eg. Weekday/Weekend) : ")
        prediction_request = predict_energy_pb2.Features(BuildingType = buildingType,
                                                     SquareFootage = squareFootage,
                                                     NumberofOccupants = noOfOccupants,
                                                     AppliancesUsed = noOfAppliances,
                                                     AverageTemperature = avgTemp,
                                                     DayofWeek = dayOfWeek
                                                     )
        prediction_response = prediction_stub.predictconsumption(prediction_request)
        print("The predicted consumption is: " + str(prediction_response.EnergyConsumption) + " KWh")

if __name__ == "__main__":
    main()