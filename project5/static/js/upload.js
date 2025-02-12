function uploadFiles() {
    var formData = new FormData(document.getElementById('uploadForm'));

    $.ajax({
        url: '/upload',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            $('#responseMessage').html('<div class="alert alert-success">Upload successful!</div>');
            console.log(response);
        },
        error: function(error) {
            $('#responseMessage').html('<div class="alert alert-danger">Upload failed: ' + error.responseJSON.message + '</div>');
            console.log(error);
        }
    });
}
