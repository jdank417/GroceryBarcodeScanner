function showInputField() {
    const selectOption = document.getElementById('input-select').value;
    const photoInput = document.getElementById('photo-input');
    const barcodeInput = document.getElementById('barcode-input');
    const cameraInput = document.getElementById('camera-input');

    photoInput.style.display = 'none';
    barcodeInput.style.display = 'none';
    cameraInput.style.display = 'none';

    if (selectOption === 'photo') {
        photoInput.style.display = 'block';
    } else if (selectOption === 'barcode') {
        barcodeInput.style.display = 'block';
    } else if (selectOption === 'camera') {
        cameraInput.style.display = 'block';
        startCamera();
    }
}

function startCamera() {
    const video = document.getElementById('camera-stream');
    const constraints = {video: {facingMode: "environment"}};

    navigator.mediaDevices.getUserMedia(constraints)
        .then((stream) => {
            video.srcObject = stream;
            video.style.display = 'block';
        })
        .catch((err) => {
            console.error('Error accessing camera: ' + err);
        });
}

function captureImage() {
    const video = document.getElementById('camera-stream');
    const canvas = document.getElementById('camera-canvas');
    canvas.style.display = 'block';

    const context = canvas.getContext('2d');


    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    document.getElementById('take-photo').style.display = 'none';
    document.getElementById('cancel-photo').style.display = 'inline-block';
    document.getElementById('retake-photo').style.display = 'inline-block';
    document.getElementById('proceed-photo').style.display = 'inline-block';
    video.style.display = 'none';
}

function resetCameraButtons() {
    const video = document.getElementById('camera-stream');
    const canvas = document.getElementById('camera-canvas');
    document.getElementById('take-photo').style.display = 'inline-block';
    document.getElementById('cancel-photo').style.display = 'none';
    document.getElementById('retake-photo').style.display = 'none';
    document.getElementById('proceed-photo').style.display = 'none';
    video.style.display = 'block';
    canvas.style.display = 'none';

}

function submitForm(e) {
    console.log('что-то произошло');
    $('form').submit(function (e) {
        const $form = $(this);
        $.ajax({
            type: $form.attr('method'),
            url: $form.attr('action'),
            data: new FormData($form, [0])
        }).done(function () {
            console.log('success');
        }).fail(function () {
            console.log('fail');
        });
        // e.preventDefault();
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('captureForm');

    document.getElementById('input-select').addEventListener('change', showInputField);

    document.getElementById('take-photo').addEventListener('click',
        captureImage
    );

    document.getElementById('cancel-photo').addEventListener('click', resetCameraButtons);
    document.getElementById('retake-photo').addEventListener('click', resetCameraButtons);
    document.getElementById('proceed-photo').addEventListener('click', submitForm);

    document.getElementById('retake-photo').style.display = 'none';
    document.getElementById('proceed-photo').style.display = 'none';
});

document.getElementById('proceed-photo').addEventListener('click', function () {
    // Add functionality to process the image and look up the barcode
});