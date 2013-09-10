$(function() {

    // TODO get this from datazilla pages JSON, 34 is "cold_load_time" test
    // which happens to be the only test we support, for now
    var page_id = 16,
        max_time = 100,
        branch = 'master',
        // browser app
        test_id = 2,
        page_name = 'cold_load_time';
        range = 7;

    datazilla_url = 'https://datazilla.mozilla.org/b2g/testdata/test_values' +
                    '?branch=master' +
                    '&test_ids=' + test_id +
                    '&page_name=' + page_name +
                    '&range=' + range;
    $.getJSON(datazilla_url, function(data) {
        // "page_id" is actually the test id
        var series = {data: [], max: undefined, min: undefined,
                      min_date: undefined, max_date: undefined,
                      last_value: undefined};

        $.each(data, function(index, value) {
            if (value.page_id == page_id) {
                if (value.avg > series.max || series.max === undefined) {
                    series.max = value.avg;
                }
                if (value.avg < series.min || series.min === undefined) {
                    series.min = value.avg;
                }

                if (value.date_run > series.max_date ||
                    series.max_date === undefined) {
                    series.max_date = value.date_run;
                }
                if (value.date_run < series.min_date ||
                    series.min_date === undefined) {
                    series.min_date = value.date_run;
                }

                if (value.date_run > series.last_date ||
                    series.last_date === undefined) {
                    series.last_date = value.date_run;
                    series.last_value = value.avg;
                }

                series.data.push([value.date_run * 1000, value.avg]);
            }
        });

        if (series.last_value >= max_time) {
            $('#perfwarning').html('warning - last test run took longer than ' +
                                   max_time + 'ms');
        }

        $('#performance').css('background-image', 'url()');
        graph(series);
    });
});

function graph(series) {
    var data = series.data;

    var margin = {top: 20, right: 15, bottom: 60, left: 60},
        width = 600 - margin.left - margin.right,
        height = 400 - margin.top - margin.bottom;

    var x = d3.time.scale()
              .domain([series.min_date * 1000, series.max_date * 1000])
              .range([ 0, width ]);

    var y = d3.scale.linear()
              .domain([d3.min(data, function(d) { return d[1]; }),
                       d3.max(data, function(d) { return d[1]; })])
              .range([ height, 0 ]);

    var chart = d3.select('#perfchart')
    .append('svg:svg')
    .attr('width', width + margin.right + margin.left)
    .attr('height', height + margin.top + margin.bottom)
    .attr('class', 'chart');

    var main = chart.append('g')
    .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
    .attr('width', width)
    .attr('height', height)
    .attr('class', 'main');

    // draw the x axis
    var xAxis = d3.svg.axis()
    .scale(x)
    .orient('bottom');

    main.append('g')
    .attr('transform', 'translate(0,' + height + ')')
    .attr('class', 'main axis date')
    .call(xAxis);

    // draw the y axis
    var yAxis = d3.svg.axis()
    .scale(y)
    .orient('left');

    main.append('g')
    .attr('transform', 'translate(0,0)')
    .attr('class', 'main axis date')
    .call(yAxis);

    var g = main.append('svg:g');

    g.selectAll('scatter-dots')
      .data(data)
      .enter().append('svg:circle')
      .attr('cx', function (d,i) { return x(d[0]); } )
      .attr('cy', function (d) { return y(d[1]); } )
      .attr('r', 5)
      .on('mouseover', function(d) {
        $('#perfinfo').html(d[1] + 'ms, ' + new Date(d[0]));
      })
      .on('mouseout', function() {
        $('#perfinfo').html('&nbsp;');
      });
}
