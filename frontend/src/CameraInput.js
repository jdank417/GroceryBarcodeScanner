import React, {useEffect, useRef, useState} from 'react';
import axios from 'axios';

const CameraInput = ({setItemData, setError}) => {
    const videoRef = useRef(null);
    const [stream, setStream] = useState(null);

    useEffect(() => {
        const startVideo = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: "environment"}});
                videoRef.current.srcObject = stream;

                const playPromise = videoRef.current.play();
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        console.log('Playback started');
                    }).catch((error) => {
                        console.error('Playback failed:', error);
                    });
                }

                setStream(stream);
            } catch (err) {
                console.error('Error accessing camera: ', err);
            }
        };

        startVideo();

        return () => {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        };
    }, [stream]);

    const captureImage = () => {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = videoRef.current.videoWidth;
        canvas.height = videoRef.current.videoHeight;
        context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);

        canvas.toBlob((blob) => {
            if (blob) {
                const formData = new FormData();
                formData.append("file", blob, "barcode.jpg");

                axios.post("http://localhost:44456/upload", formData)
                    .then((response) => {
                        setItemData(response.data);
                        setError('');
                    })
                    .catch((error) => {
                        setError(error.response.data.error);
                        setItemData(null);
                    });
            } else {
                console.error("Failed to create Blob from canvas");
            }
        }, "image/jpeg");
    };

    return (
        <div id="camera-input">
            <video ref={videoRef} id="camera-stream" autoPlay playsInline></video>
            <div id="camera-frame"></div>
            <div className="camera-buttons">
                <button type="button" onClick={captureImage}>Take Photo</button>
                <button type="button" onClick={() => videoRef.current.play()}>Cancel</button>
                <button type="button" onClick={() => videoRef.current.play()}>Retake</button>
            </div>
        </div>
    );
};

export default CameraInput;
