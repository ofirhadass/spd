window.setLike = setLike;

function setLike(likeButton, transId) {
    var word = document.getElementById("word-title").innerHTML;
    var translation = document.getElementById("trans" + transId).innerHTML;
    if (likeButton.innerHTML === "like") {
        likeButton.innerHTML = "dislike";
    }
    else {
        likeButton.innerHTML = "like";
    }

    fetch('/like/' + word + '/' + translation);
}