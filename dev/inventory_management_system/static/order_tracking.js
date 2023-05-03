function updateAll() {
  $.ajax({
    type: "GET",
    url: "order_station_tables",
    dataType: "json",
    success: function (response) {
      if (response != null) {
        $("#neworders").html(response["open"]);
        $("#stations").html(response["stations"]);
        $("#finishedorders").html(response["finished"]);

        $("#new_order_count").text(
          parseInt(response["counts"]["OPEN"]).toLocaleString("en-US")
        );
        $("#finished_order_count").text(
          parseInt(response["counts"]["COMPLETE"]).toLocaleString("en-US")
        );
      }
    },
    error: function (data) {
      console.log("error");
    },
  });
}
