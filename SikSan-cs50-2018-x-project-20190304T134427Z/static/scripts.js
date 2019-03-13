// проверка хода второго игрока
function roundReady(sessionId) {
    return function() {
        $.ajax({
            url: '/round_end/' + sessionId,
            type: 'post',
            success: function(response) {
                console.log('roundReady', response)
                if (response === true) location.replace("/fight/" + sessionId);
            }
        });
    }
}

// проверка подключения второго игрока к игре
function checkplayer(sessionId) {
    return function() {
        $.ajax({
            url: '/checkplayer/' + sessionId,
            type: 'post',
            success: function(response) {
                console.log('checkplayer', response)
                if (response === true) location.reload();
            }
        });
    }
}

// проверка изменения заявок на игру
function indexRefresh(challenges) {
    return function() {
        console.log('indexRefresh', challenges);

        $.ajax({
            url: '/index_refresh/',
            type: 'post',
            data: JSON.stringify(challenges),
            contentType: 'applications/json',
            success: function(response) {
                console.log('indexRefresh', response);
                if (response === true) location.reload();
            }
        });
    };
}

// каждую секунду включает checkplayer
function waitingPlayerScript(sessionId) {
    console.log('sessionId', sessionId)
    $(document).ready(function() {
        setInterval(checkplayer(sessionId), 1000);
    });
}

// каждую секунду включает roundReady
function waitingScript(sessionId) {
    console.log('waitingScript', sessionId)
    $(document).ready(function() {
        setInterval(roundReady(sessionId), 1000);
    });
}

// каждую секунду включает indexRefresh
function indexScript(challenges) {
    console.log('indexScript', challenges)
    $(document).ready(function() {
        setInterval(indexRefresh(challenges), 3000);
    });
}

const TIMEOUT = 60000 // 60s
const UPDATE_INTERVAL = 1000 // 1s

function startTimer($timer, timeout = TIMEOUT, updateInterval = UPDATE_INTERVAL) {
    function updateTimer(leftTime = timeout) {
        $timer.innerHTML = leftTime / 1000

        if (leftTime <= 0) {
            return setTimeout(() => alert('Best chances are gone'), 60)
        }

        setTimeout(() => updateTimer(leftTime - updateInterval), updateInterval)
    }

    updateTimer()
}

$(document).ready(function() {
    if (window.timer) startTimer(window.timer)
});
