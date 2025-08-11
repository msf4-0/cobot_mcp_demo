from ultralytics import YOLO

if __name__ == '__main__':
    name = "shapes_detection"
    data_path = 'C:/Users/User/Documents/reuben_ws/cobot_agentic_ai/Shapes_Dataset_yolov8/data.yaml'
    n_epochs = 50
    batch_size = 16
    n_workers = 8
    gpu_id = 0
    verbose = True
    rng = 0
    validate = True
    patience = 0
    project = 'C:/Users/User/Documents/reuben_ws/cobot_agentic_ai/src/models'
    save_period=5
    # model = YOLO('C:/Users/User/Documents/reuben_ws/cobot_agentic_ai/src/models/yolov8n.pt')
    model = YOLO('C:/Users/User/Documents/reuben_ws/cobot_agentic_ai/src/models/shapes_detection/weights/first_50_epoch/last.pt')

    results = model.train(
        data=data_path,
        epochs=n_epochs,
        batch=batch_size,
        device=gpu_id,
        verbose=verbose,
        seed=rng,
        val=validate,
        project=project,
        name=name,
        workers=n_workers,
        patience=patience,
        save_period=save_period
    )