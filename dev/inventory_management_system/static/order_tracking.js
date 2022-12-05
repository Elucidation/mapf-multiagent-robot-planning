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

function updateNewOrders() {
    $.ajax({
        type: "GET",
        url: "orders/open",
        dataType: "html",
        success: function (response) {
            if (response != null) {
            $("#neworders").html(response)
            }
        },
        error: function (data) {
            console.log('error');
        }
    });
}


function updateStations() {
    $.ajax({
        type: "GET",
        url: "stations",
        dataType: "html",
        success: function (response) {
            if (response != null) {
            $("#stations").html(response)
            }
        },
        error: function (data) {
            console.log('error');
        }
    });
}



function updateFinishedOrders() {
    $.ajax({
        type: "GET",
        url: "orders/finished",
        dataType: "html",
        success: function (response) {
            if (response != null) {
            $("#finishedorders").html(response)
            }
        },
        error: function (data) {
            console.log('error');
        }
    });
}
