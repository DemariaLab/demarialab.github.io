function onDOMReady(){
	 
		 const underline = document.querySelector('.underline');
        const navItems = document.querySelectorAll('.nav-item');
        const activeItem = document.querySelector('.nav-item.active d');
        const isHomePage = window.location.pathname === '/';
	
	
  var header = document.querySelector("header");
 
   const navbar = document.querySelector('.navbar');
       
       
        function updateUnderline(item) {
			if (item){
				underline.style.transform = 'scaleX(1)';
			const headerRect= header.getBoundingClientRect();
            const itemRect = item.getBoundingClientRect();
if(itemRect.width>0){
			underline.style.width = itemRect.width + 'px';
            underline.style.left = itemRect.left + 'px';
            underline.style.top  =(itemRect.bottom ) + 'px';
			
			
            underline.style.display = 'block'; // Display the underline once its position is set
			}}else{
				 underline.style.transform = 'scaleX(0)';
			}
		}

		
        [...navItems].forEach(item => {
            item.addEventListener('mouseover', function() {
                updateUnderline(item);
            });
			
            item.addEventListener('mouseout', function() {
                 updateUnderline(activeItem);
            });
        });
		
		requestAnimationFrame(() => {
  
   if (activeItem) {
            updateUnderline(activeItem);
        } 
});
		
       
		}



function getScaleX(div) {
    const transformValue = window.getComputedStyle(div).getPropertyValue('transform');
    
    // Parse the transform value to get the scaleX value
    const match = transformValue.match(/matrix\(([^)]+)\)/);
    if (match) {
        const matrixValues = match[1].split(', ');
        const scaleX = parseFloat(matrixValues[0]);
        return(scaleX);
    } else {
       return(0);
    }
}

document.addEventListener("DOMContentLoaded", function() {
  onDOMReady();
});
