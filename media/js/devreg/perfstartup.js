(function() {
    var $button = $('#perf_startup');
    var link = $button.attr('href');
    $button.click(function(event){
        event.preventDefault();
        $.get(link, function(data) {
            if (data.hasOwnProperty('uuid')) {
                console.log('startup test queued: ' + data['uuid']);
            }
        });
    });
})();
