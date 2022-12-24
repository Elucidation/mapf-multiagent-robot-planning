function updateAll() {
    $.ajax({
        type: "GET",
        url: "order_station_tables",
        dataType: "json",
        success: function (response) {
            if (response != null) {
            $("#neworders").html(response['open'])
            $("#stations").html(response['stations'])
            $("#finishedorders").html(response['finished'])
            }
        },
        error: function (data) {
            console.log('error');
        }
    });
}