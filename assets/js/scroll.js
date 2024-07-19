function onDOMReady() {
    const underline = document.querySelector('.underline');
    const navItems = document.querySelectorAll('.nav-item');
    const activeItem = document.querySelector('.nav-item.active d');
    const header = document.querySelector("header");

    function updateUnderline(item) {
        if (item) {
            underline.style.transform = 'scaleX(1)';
            const itemRect = item.getBoundingClientRect();
            if (itemRect.width > 0) {
                underline.style.width = itemRect.width + 'px';
                underline.style.left = itemRect.left + 'px';
                underline.style.top = (itemRect.bottom) + 'px';
                underline.style.display = 'block'; // Display the underline once its position is set
            }
        } else {
            underline.style.transform = 'scaleX(0)';
        }
    }

    [...navItems].forEach(item => {
        item.addEventListener('mouseover', function () {
            updateUnderline(item);
        });

        item.addEventListener('mouseout', function () {
            updateUnderline(activeItem);
        });
    });

    requestAnimationFrame(() => {
        if (activeItem) {
            updateUnderline(activeItem);
        }
    });
}


function linkTo_UnCryptMailto(encoded) {
    let decoded = atob(encoded); // Decode the email address
    let linkElement = document.getElementById('emailLink'); // Get the link element by ID
    linkElement.innerHTML = "Email: " + decoded; // Replace the link text with the email address
}

document.addEventListener("DOMContentLoaded", function () {
    onDOMReady();
});
