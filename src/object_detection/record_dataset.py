import cv2
import os
import time

def record_image_dataset(output_folder="image_dataset", fps=10):
    """
    Records images from a camera at a specified FPS and saves them as PNG files.

    Args:
        output_folder (str): The folder where the images will be saved.
        fps (int): The desired frames per second to record images.
    """

    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")

    # Open the default camera
    cap = cv2.VideoCapture(0)

    # Check if camera opened successfully
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    # Calculate the delay needed between frames to achieve the desired FPS
    frame_interval = 1.0 / fps
    last_capture_time = time.time()
    frame_count = 0

    print(f"Recording images at {fps} FPS. Press 'q' to quit.")

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("Error: Could not read frame from camera.")
                break

            # Display the live feed
            cv2.imshow("Live Feed - Press 'q' to Quit", frame)

            current_time = time.time()
            if current_time - last_capture_time >= frame_interval:
                # Construct the filename
                timestamp = int(current_time * 1000)  # Milliseconds since epoch
                image_filename = os.path.join(output_folder, f"image_{timestamp:013d}.png")

                # Save the frame as a PNG image
                cv2.imwrite(image_filename, frame)
                print(f"Saved {image_filename}")

                last_capture_time = current_time
                frame_count += 1

            # Break the loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Recording interrupted by user.")
    finally:
        # Release the camera and destroy all OpenCV windows
        cap.release()
        cv2.destroyAllWindows()
        print("Recording stopped. Camera released.")

if __name__ == "__main__":
    time.sleep(1)
    record_image_dataset(output_folder="C:/Users/User/Documents/reuben_ws/cobot_agentic_ai/src/object_detection/images/diamond_triangle", fps=5)