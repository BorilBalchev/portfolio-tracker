const selectButtons = document.querySelectorAll(".select-btn"),
        items = document.querySelectorAll(".item");


window.onload = function(){
    var startDate = document.getElementById('start');
    var endDate = document.getElementById('end');

    endDate.setAttribute("value", new Date().toLocaleDateString('en-GB').split('/').reverse().join("-"));
    startDate.setAttribute("value", new Date(new Date().setFullYear(new Date().getFullYear() - 1)).toLocaleDateString('en-GB').split('/').reverse().join('-'));
}


selectButtons.forEach(selectBtn => {
    selectBtn.addEventListener("click", () => {
        selectBtn.classList.toggle("open");
    })
})


items.forEach(item => {
    let label = item.getElementsByTagName('label')[0];
    label.addEventListener("click", () => {
        type = label.parentElement.parentElement.id;
        if (type === "sma"){
            item.classList.toggle("checked-sma");
        }
        else if (type === "ema"){
            item.classList.toggle("checked-ema");
        }
        else if (type === "oscillators"){
            item.classList.toggle("checked-oscillators");
        }
        else if (type === "vwma"){
            item.classList.toggle("checked-vwma");
        }

        let checked_sma = document.querySelectorAll(".checked-sma"),
            checked_ema = document.querySelectorAll(".checked-ema"),
            checked_vwma = document.querySelectorAll(".checked-vwma"),
            checked_oscillators = document.querySelectorAll(".checked-oscillators"),
            btnText = document.querySelectorAll(".btn-text");
            console.log(btnText);
            
            if (type === "sma"){
                console.log(checked_sma.length);
                if (checked_sma.length == 1){
                    btnText[0].innerHTML = `${checked_sma.length} SMA period selected`
                }
                else if (checked_sma && checked_sma.length > 0){
                    btnText[0].innerHTML = `${checked_sma.length} SMA periods selected`
                }
                else{
                    btnText[0].innerHTML = `Select SMA period(s)`
                }
            }

            else if (type === "ema"){
                console.log(checked_ema.length);
                if (checked_ema.length == 1){
                    btnText[1].innerHTML = `${checked_ema.length} EMA period selected`
                }
                else if (checked_ema && checked_ema.length > 0){
                    btnText[1].innerHTML = `${checked_ema.length} EMA periods selected`
                }
                else{
                    btnText[1].innerHTML = `Select EMA period(s)`
                }
            }

            if (type === "vwma"){
                console.log(checked_vwma.length);
                if (checked_vwma.length == 1){
                    btnText[2].innerHTML = `${checked_vwma.length} VWMA period selected`
                }
                else if (checked_vwma && checked_vwma.length > 0){
                    btnText[2].innerHTML = `${checked_vwma.length} VWMA periods selected`
                }
                else{
                    btnText[2].innerHTML = `Select VWMA period(s)`
                }
            }

            if (type === "oscillators"){
                console.log(checked_oscillators);
                if (checked_oscillators.length == 1){
                    btnText[3].innerHTML = `${checked_oscillators.length} Oscillator selected`
                }
                else if (checked_oscillators && checked_oscillators.length > 0){
                    btnText[3].innerHTML = `${checked_oscillators.length} Oscillators selected`
                }
                else{
                    btnText[3].innerHTML = `Select Oscillator(s)`
                }
            }
    })
})