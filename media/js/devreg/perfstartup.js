(function() {
    var $button = $('#perf_startup');
    var link = $button.attr('href');
    $button.click(function(event){
        event.preventDefault();
        $.get(link, function(data) {
            console.log('startup test queued: ' + data);
        });
    });
})();
