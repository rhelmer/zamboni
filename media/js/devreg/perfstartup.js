(function() {
    var $button = $('#perf_startup');
    var link = $button.attr('href');
    $button.click(function(event){
        event.preventDefault();
        $.get(link, function(data) {
            if (data.hasOwnProperty('uuid')) {
                if (data.uuid == null) {
                    console.log('startup test already queued');
                } else {
                    console.log('startup test queued: ' + data['uuid']);
                }
                $button.addClass('disabled');
            }
        });
    });
})();
