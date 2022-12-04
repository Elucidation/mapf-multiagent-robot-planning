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
