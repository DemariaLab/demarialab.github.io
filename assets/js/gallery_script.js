function getItemsToShow() {
    const width = window.innerWidth;
    if (width >= 2500) return 7;
    if (width >= 2000) return 5;
    if (width >= 768) return 3;
    return 1;
}

let currentIndex = 0;
let firstItemOffset = NaN;
let isAnimating = false;

function scrollToSlide(index) {
    // showSlides(index);
}

function showSlides(index) {
    if (isAnimating) return;

    isAnimating = true;
    const items = document.querySelectorAll('.slideshow-inner .slideshow-item');
    const totalItems = items.length;

    if (totalItems === 0) {
        isAnimating = false;
        return;
    }

    if (isNaN(firstItemOffset)) {
        firstItemOffset = parseInt(items[0].dataset.slideIndex);
    }

    let itemsToShow = getItemsToShow();
    if (totalItems <= itemsToShow) {
        itemsToShow = itemsToShow % 2 === 0 ? itemsToShow + 1 : itemsToShow;
    }

    const halfItemsToShow = Math.floor(itemsToShow / 2);
    currentIndex = (index < 0) ? totalItems - Math.abs(index) : index;

    const colClasses = Array.from({length: 12}, (_, i) => `col-${i + 1}`);
    items.forEach(item => {
        item.classList.add('col-auto', 'me-1', 'me-lg-2');
        item.classList.remove(...colClasses);
        item.style.width = '0%';
    });

    const mainImageWidth = 60;
    const actualMainItemIndex = (currentIndex % totalItems) + firstItemOffset;
    const relativeMainItemIndex = currentIndex % totalItems;

    const itemMain = Array.from(items).find(item => parseInt(item.dataset.slideIndex) === actualMainItemIndex);
    if (!itemMain) {
        console.error(`Couldn't find item with index ${actualMainItemIndex}`);
        isAnimating = false;
        return;
    }

    itemMain.style.width = itemsToShow === 1 ? '100%' : `${mainImageWidth}%`;

    const lastItemIndex = firstItemOffset + totalItems - 1;
    const lowerLimit = actualMainItemIndex - halfItemsToShow;
    const upperLimit = actualMainItemIndex + halfItemsToShow + Math.max(halfItemsToShow - relativeMainItemIndex, 0);

    const sideItems = Array.from(items).filter(item => {
        const slideIndex = parseInt(item.dataset.slideIndex);
        let adjustedLowerLimit = lowerLimit;

        if (upperLimit > lastItemIndex) {
            adjustedLowerLimit -= (upperLimit - lastItemIndex);
        }

        const isSideItem = slideIndex >= adjustedLowerLimit && slideIndex <= upperLimit && slideIndex !== actualMainItemIndex;
        if (!isSideItem && slideIndex !== actualMainItemIndex) {
            item.classList.remove('me-1', "me-lg-2");
            item.style.width = "0%";
        }
        return isSideItem;
    });

    const sideItemWidth = (100 - mainImageWidth) / sideItems.length;
    sideItems.forEach(item => {
        item.style.width = `${sideItemWidth}%`;
    });

    setTimeout(() => {
        isAnimating = false;
    }, 500);
}

function nextSlide() {
    showSlides(currentIndex + 1);
}

function prevSlide() {
    showSlides(currentIndex - 1);
}

window.addEventListener('resize', () => showSlides(currentIndex));
document.addEventListener('DOMContentLoaded', () => showSlides(currentIndex));
