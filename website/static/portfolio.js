var counter = 15;
var lastPrices = {};

function startUpdateCycle(){
    updatePrices();
    setInterval(function (){
        counter--;
        $('#counter').text(counter + 1);
        if (counter <= 0) {
            updatePrices();
            counter = 15;
        }
    }, 1000);
}


$(document).ready(function(){
    startUpdateCycle();
});


function deleteTicker(tickerId){
    fetch('/delete-ticker', {
        method: 'POST',
        body: JSON.stringify({ tickerId: tickerId })
    }).then((_res) => {
        window.location.href = '/';
    })
}


function editAmount(id, amount){
    $('#item-id').val(id);
    $('#item-value').val(amount);
    $('#editModal').modal('show');
}


function saveValue(){
    var id = $('#item-id').val();
    var amount = $('#item-value').val();

    $.ajax({
        url: '/update_amount',
        type: 'POST',
        data: {
            'id': id,
            'value': amount
        },
        success: function(response) {
            if (response.success) {
                $('#value-' + id).text(amount);
                $('#editModal').modal('hide');
                updatePrices();
            } else {
                alert('Failed to update value. Enter a positive number');
            }
        }
    });
}


function updatePrices(){
    const ul = document.getElementById('tickers');
    const listItems = ul.getElementsByTagName('tr');
    const itemsArray = Array.from(listItems);
    itemsArray.shift();
    let tickers = [];
    itemsArray.forEach(item => {
        tickers.push(item.id)
    });
    let values = [];
    let balance = document.getElementById('balance');
    let sum = 0;
    tickers.forEach(function(ticker){
        $.ajax({
            url: '/get_stock_data',
            type: 'POST',
            data: JSON.stringify({'ticker': ticker}),
            contentType: 'application/json; charset=utf-8',
            dataType: 'json',
            success: function(data){
                var changePercent = ((data.currentPrice - data.openPrice) / data.openPrice) * 100;

                var colorClass;
                if (changePercent <= -2){
                    colorClass = 'red'
                }
                else if (changePercent < 0){
                    colorClass = 'dark-red'
                }
                else if (changePercent == 0){
                    colorClass = 'gray'
                }
                else if (changePercent <= 2){
                    colorClass = 'dark-green'
                }
                else{
                    colorClass = 'green'
                }
                var options = { style: 'currency', currency: 'USD' };
                var formatter = new Intl.NumberFormat('en-US', options);
                $(`#${ticker}-price`).text(`${formatter.format(data.currentPrice.toFixed(2))}`);
                $(`#${ticker}-pct`).text(`${changePercent.toFixed(2)}%`);
                let price = data.currentPrice.toFixed(2);
                let amount = parseFloat(document.getElementById(`${ticker}-amount`).textContent);
                let value = parseFloat((price * amount).toFixed(2));
                sum += value;
                console.log(sum);
                balance.innerHTML = formatter.format(sum.toFixed(2));
                $(`#${ticker}-value`).text(`${formatter.format(value)}`);
                $(`#${ticker}-price`).removeClass('dark-red red gray green dark-green').addClass(colorClass);
                $(`#${ticker}-pct`).removeClass('dark-red red gray green dark-green').addClass(colorClass);

                var flashClass;
                if (lastPrices[ticker] > data.currentPrice){
                    flashClass = 'red-flash';
                }
                else if (lastPrices[ticker] < data.currentPrice){
                    flashClass = 'green-flash';
                }
                else{
                    flashClass = 'gray-flash';
                }
                lastPrices[ticker] = data.currentPrice;

                $(`#${ticker}-price`).addClass(flashClass);
                $(`#${ticker}-pct`).addClass(flashClass);
                setTimeout(function(){
                    $(`#${ticker}-price`).removeClass(flashClass);
                    $(`#${ticker}-pct`).removeClass(flashClass);
                }, 1000);

            }
        });
    });
}