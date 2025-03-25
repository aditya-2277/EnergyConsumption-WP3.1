import grpc
from concurrent import futures

import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib

import train_model_pb2
import train_model_pb2_grpc

class TrainingServicer(train_model_pb2_grpc.TrainingServicer):
    def trainmodel(self, request, context):
        try:
            df = pd.read_csv(request.csv_file_path)

            building_type_map = {"Residential": 1, "Commercial": 2, "Industrial": 3}
            day_of_week_map = {"Weekday": 1, "Weekend": 2}

            df["Building Type"] = df["Building Type"].map(building_type_map)
            df["Day of Week"] = df["Day of Week"].map(day_of_week_map)

            independentVariables = df.iloc[:, :-1]
            dependentVariable = df.iloc[:, -1]

            model = LinearRegression()
            model.fit(independentVariables.values, dependentVariable)

            joblib.dump(model,"model.pkl")
            return train_model_pb2.TrainResponse(status="Training Completed!!")
        except Exception as e:
            return train_model_pb2.TrainResponse(status=f"Error:{str(e)}")

def serve():
    port = "8062"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    train_model_pb2_grpc.add_TrainingServicer_to_server(TrainingServicer(),server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Training Service is running on port: " + port)
    server.wait_for_termination()

if __name__ == "__main__":
    serve()