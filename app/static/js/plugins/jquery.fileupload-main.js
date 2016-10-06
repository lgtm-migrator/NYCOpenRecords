/* global $, window */

$(function () {
    'use strict';

    function setRemoveBtn(button, sendDelete) {
        sendDelete = typeof sendDelete !== 'undefined' ? sendDelete : true;
        button.removeClass('hidden');
        button.click(function(e) {
            e.preventDefault();
            var template = $(this).closest('.template-download');
            if (sendDelete) {
                $.ajax({
                    type: 'DELETE',
                    url: '/upload/request/' +
                        'FOIL-XXX/' +
                        idToName(template.attr('id'))
                });
            }
            template.remove();
        });
    }

    function pollUploadStatus(upload_filename, htmlId) {
        /*
        Sends a request to the upload status endpoint
        every 2 seconds until it receives a message indicating
        the upload has completed or until it receives an error
        message and updates the download template.
         */
        $.ajax({
            type: 'GET',
            url: '/upload/status',
            data: {
                request_id: "FOIL-XXX",
                filename: upload_filename
            },
            dataType: 'json',
            success: function(response) {
                if (response.error) {
                    // Reveal error message
                    var tr = $('#'.concat(htmlId));
                    tr.find(".error-post-fileupload").removeClass('hidden');
                    tr.find(".error-post-fileupload-msg").text("Error processing file.");  // scanning, really
                    tr.find(".processing-upload").remove();
                    setRemoveBtn(tr.find(".remove-post-fileupload"),
                        false);  // file already deleted
                }
                else if (response.status != "ready") {
                    setTimeout(pollUploadStatus.bind(
                        null, upload_filename, htmlId
                    ), 2000);
                }
                else {
                    // Reveal full template
                    var tr = $('#'.concat(htmlId));
                    tr.find(".fileupload-input-fields").removeClass('hidden');
                    tr.find(".processing-upload").remove();
                    setRemoveBtn(tr.find(".remove-post-fileupload"));
                }
            }
        });
    }

    function nameToId(name) {
        /*
        Returns an encoded version of 'name' with no trailing '='.
         */
        return window.btoa(name).replace(/=/g, '');
    }

    function idToName(id) {
        /*
        Returns an unencoded of 'id'.
         */
        return window.atob(id);
    }

    // Initialize the jQuery File Upload widget:
    $('#fileupload').fileupload({
        // Uncomment the following to send cross-domain cookies:
        //xhrFields: {withCredentials: true},
        url: '/upload/FOIL-XXX',
        maxChunkSize: 512000,  // 512 kb
        maxFileSize: 500000000,  // 500 mb
        // autoUpload: true,
        chunksend: function(e, data) {
            if (data.context[0].abortChunkSend) {
                return false;
            }
        },
        chunkdone: function(e, data) {
            // stop sending chunks on error
            if (data.result) {
                if (data.result.files[0].error) {
                    data.context[0].abortChunkSend = true;
                    data.files[0].error = data.result.files[0].error
                }
            }
        },
        chunkfail: function(e, data) {
            // remove existing partial upload
            $.ajax({
                type: "DELETE",
                url: '/upload/request/' +
                     'FOIL-XXX/' +
                     data.files[0].name
            });
        }
    }).bind('fileuploaddone', function (e, data) {
        var filename = data.result.files[0].name;
        var htmlId = nameToId(filename);
        data.result.files[0].identifier = htmlId;
        setTimeout(
            pollUploadStatus.bind(null, filename, htmlId),
            4000); // McAfee Scanner min 3+ sec startup
    });

    // // Load existing files:
    // $('#fileupload').addClass('fileupload-processing');
    // $.ajax({
    //     // Uncomment the following to send cross-domain cookies:
    //     //xhrFields: {withCredentials: true},
    //     url: $('#fileupload').fileupload('option', 'url'),
    //     dataType: 'json',
    //     context: $('#fileupload')[0]
    // }).always(function () {
    //     $(this).removeClass('fileupload-processing');
    // }).done(function (result) {
    //     $(this).fileupload('option', 'done')
    //         .call(this, $.Event('done'), {result: result});
    // });

});
