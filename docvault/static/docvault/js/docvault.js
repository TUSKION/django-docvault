/**
 * DocVault Common JavaScript
 * This file contains common functionality used across DocVault pages
 */

document.addEventListener('DOMContentLoaded', function() {
    // Store heading elements and their positions for scroll tracking
    let headingElements = [];
    let headingPositions = [];
    
    /**
     * Process heading tags to add IDs for anchor links
     * This allows for direct linking to sections via URL fragments
     */
    function processHeadings() {
        const documentBody = document.getElementById('document-body');
        if (!documentBody) return;
        
        // Find all headings in the document content
        const headings = documentBody.querySelectorAll('h1, h2, h3, h4, h5, h6');
        headingElements = Array.from(headings);
        
        headingElements.forEach(function(heading) {
            // Generate ID from heading text if it doesn't already have one
            if (!heading.id) {
                const headingText = heading.textContent.trim();
                let headingId = headingText.toLowerCase()
                    .replace(/[^\w\s-]/g, '')  // Remove special chars
                    .replace(/\s+/g, '-')      // Replace spaces with hyphens
                    .replace(/^-+|-+$/g, '');  // Remove leading/trailing hyphens
                
                // Ensure the ID is unique if there are duplicate headings
                let uniqueId = headingId;
                let counter = 1;
                while (document.getElementById(uniqueId)) {
                    uniqueId = headingId + '-' + counter;
                    counter++;
                }
                
                // Set the ID attribute
                heading.id = uniqueId;
            }
        });
        
        // Calculate positions after a brief delay to ensure layout is complete
        setTimeout(calculateHeadingPositions, 100);
    }
    
    /**
     * Calculate and store the vertical positions of all headings
     * Used for determining which section is currently in view
     */
    function calculateHeadingPositions() {
        headingPositions = headingElements.map(function(heading) {
            return {
                id: heading.id,
                top: heading.getBoundingClientRect().top + window.pageYOffset - 100 // Offset for fixed header
            };
        });
    }
    
    /**
     * Determine which heading is currently active based on scroll position
     * Highlights the corresponding TOC item
     */
    function updateActiveTocItem() {
        if (headingPositions.length === 0) return;
        
        const scrollPosition = window.pageYOffset;
        let activeHeading = headingPositions[0].id;
        
        // Find the heading that's currently in view
        for (let i = 0; i < headingPositions.length; i++) {
            if (scrollPosition >= headingPositions[i].top) {
                activeHeading = headingPositions[i].id;
            } else {
                break;
            }
        }
        
        // Update active class on TOC links
        const tocLinks = document.querySelectorAll('#toc a');
        tocLinks.forEach(function(link) {
            link.classList.remove('active');
            if (link.getAttribute('href') === '#' + activeHeading) {
                link.classList.add('active');
            }
        });
    }
    
    /**
     * Setup smooth scrolling for table of contents links
     * Adds highlight effect when scrolling to a section
     */
    function setupTocLinks() {
        const tocLinks = document.querySelectorAll('#toc a');
        tocLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                const href = this.getAttribute('href');
                
                // Handle "Back to top" link
                if (href === '#') {
                    smoothScrollTo(0);
                    return;
                }
                
                const targetId = href.substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    // Remove active class from all links
                    tocLinks.forEach(link => link.classList.remove('active'));
                    
                    // Add active class to clicked link
                    this.classList.add('active');
                    
                    // Get the element's position and scroll to it
                    smoothScrollToElement(targetElement);
                    
                    // Add a highlight effect
                    targetElement.classList.add('highlight-heading');
                    setTimeout(function() {
                        targetElement.classList.remove('highlight-heading');
                    }, 2000);
                    
                    // Update URL hash without causing a jump
                    history.pushState(null, null, '#' + targetId);
                }
            });
        });
    }

    /**
     * Setup collapsible elements with icon rotation
     * Used for collapsible sections like the TOC
     */
    function setupCollapsibles() {
        const collapsibles = document.querySelectorAll('[data-bs-toggle="collapse"]');
        collapsibles.forEach(function(element) {
            // Handle icon rotation on click
            element.addEventListener('click', function() {
                const icon = this.querySelector('i.bi');
                if (icon) {
                    if (icon.classList.contains('bi-chevron-down')) {
                        icon.classList.replace('bi-chevron-down', 'bi-chevron-up');
                    } else {
                        icon.classList.replace('bi-chevron-up', 'bi-chevron-down');
                    }
                }
            });
            
            // Set initial icon state based on expanded state
            const targetId = element.getAttribute('data-bs-target');
            if (targetId) {
                const target = document.querySelector(targetId);
                const icon = element.querySelector('i.bi');
                if (target && icon) {
                    const isExpanded = target.classList.contains('show');
                    if (isExpanded && icon.classList.contains('bi-chevron-down')) {
                        icon.classList.replace('bi-chevron-down', 'bi-chevron-up');
                    }
                }
            }
        });
    }
    
    /**
     * Handle automatic sidebar visibility
     * If a page has table of contents, show it in sidebar
     * If no TOC is present, use full width for content
     */
    function handleSidebarVisibility() {
        const sidebar = document.querySelector('.col-md-3');
        const mainContent = document.querySelector('.col-md-9');
        
        if (!sidebar || !mainContent) return;
        
        // If the sidebar is empty or has no visible content, hide it
        const sidebarCards = sidebar.querySelectorAll('.card');
        let hasVisibleContent = false;
        
        sidebarCards.forEach(function(card) {
            const cardBody = card.querySelector('.card-body');
            if (cardBody && cardBody.children.length > 0) {
                hasVisibleContent = true;
            }
        });
        
        if (!hasVisibleContent) {
            sidebar.style.display = 'none';
            mainContent.className = 'col-12';
        }
    }

    /**
     * Setup scroll event listener for TOC highlighting
     * Handles active item highlighting and ensures visibility within the sidebar
     */
    function setupScrollListener() {
        // Throttle scroll events for better performance
        let scrollTimeout;
        window.addEventListener('scroll', function() {
            if (!scrollTimeout) {
                scrollTimeout = setTimeout(function() {
                    updateActiveTocItem();
                    // Ensure the active item is visible in the scrollable container
                    ensureActiveItemVisible();
                    scrollTimeout = null;
                }, 100);
            }
        });
        
        // Also update on window resize as positions may change
        window.addEventListener('resize', function() {
            calculateHeadingPositions();
            updateActiveTocItem();
            ensureActiveItemVisible();
        });
    }
    
    /**
     * Ensures the active TOC item is visible in the scrollable sidebar
     * Auto-scrolls the TOC container if needed
     */
    function ensureActiveItemVisible() {
        const activeLink = document.querySelector('#toc a.active');
        const tocContainer = document.querySelector('.col-md-3 .card-body');
        
        if (activeLink && tocContainer) {
            const linkRect = activeLink.getBoundingClientRect();
            const containerRect = tocContainer.getBoundingClientRect();
            
            // Check if the active link is outside the visible area
            if (linkRect.top < containerRect.top || linkRect.bottom > containerRect.bottom) {
                // Scroll the link into view with some padding
                const scrollTop = activeLink.offsetTop - (tocContainer.clientHeight / 2);
                tocContainer.scrollTo({
                    top: Math.max(0, scrollTop),
                    behavior: 'smooth'
                });
            }
        }
    }
    
    /**
     * Smooth scroll to a specific element with proper offset
     * @param {HTMLElement} element - The element to scroll to
     */
    function smoothScrollToElement(element) {
        if (!element) return;
        
        const headerOffset = 70;
        const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
        const offsetPosition = elementPosition - headerOffset;
        
        smoothScrollTo(offsetPosition);
    }
    
    /**
     * Smooth scroll to a specific Y position
     * @param {number} yPosition - The Y position to scroll to
     */
    function smoothScrollTo(yPosition) {
        // Detect if smooth scrolling is supported
        const supportsScrollBehavior = 'scrollBehavior' in document.documentElement.style;
        
        if (supportsScrollBehavior) {
            window.scrollTo({
                top: yPosition,
                behavior: 'smooth'
            });
        } else {
            // Fallback for browsers that don't support smooth scrolling
            smoothScrollFallback(yPosition);
        }
    }
    
    /**
     * Fallback smooth scrolling implementation for browsers without native support
     * @param {number} targetY - The target Y position to scroll to
     */
    function smoothScrollFallback(targetY) {
        const startY = window.pageYOffset;
        const distance = targetY - startY;
        const duration = 500; // Duration in ms
        let startTime = null;
        
        function animation(currentTime) {
            if (startTime === null) startTime = currentTime;
            const timeElapsed = currentTime - startTime;
            const progress = Math.min(timeElapsed / duration, 1);
            const easeInOutCubic = progress < 0.5 
                ? 4 * progress * progress * progress 
                : 1 - Math.pow(-2 * progress + 2, 3) / 2;
                
            window.scrollTo(0, startY + distance * easeInOutCubic);
            
            if (timeElapsed < duration) {
                requestAnimationFrame(animation);
            }
        }
        
        requestAnimationFrame(animation);
    }

    /**
     * Add tooltips and improve text handling for ToC items
     * Ensures long headings display well and show full text on hover
     */
    function setupTocTooltips() {
        const tocLinks = document.querySelectorAll('#toc a');
        tocLinks.forEach(function(link) {
            // Skip the "Back to top" link
            if (link.getAttribute('href') === '#') return;
            
            // Set the title attribute to show the full text on hover
            const fullText = link.textContent.trim();
            link.setAttribute('title', fullText);
            
            // If text is very long, add a CSS class to help with readability
            if (fullText.length > 40) {
                link.classList.add('toc-long-text');
            }
            
            // For level 4+ headings, truncate text more aggressively for better display
            const parentLi = link.parentElement;
            if (parentLi && 
                (parentLi.getAttribute('data-level') === '4' || 
                 parentLi.getAttribute('data-level') === '5' ||
                 parentLi.getAttribute('data-level') === '6')) {
                
                if (fullText.length > 30) {
                    const truncated = fullText.substring(0, 27) + '...';
                    link.setAttribute('data-full-text', fullText);
                    link.innerHTML = truncated;
                }
            }
        });
    }
    
    // Initialize functions
    try {
        processHeadings();
        setupTocLinks();
        setupCollapsibles();
        handleSidebarVisibility();
        setupTocTooltips(); // Run this before setting up scroll to ensure proper text handling
        setupScrollListener();
        
        // Initialize active TOC item
        setTimeout(function() {
            updateActiveTocItem();
            ensureActiveItemVisible(); // Make sure active item is visible on page load
        }, 200);
        
        // Handle initial hash in URL
        if (window.location.hash) {
            const targetId = window.location.hash.substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                setTimeout(function() {
                    // Scroll to element after a brief delay to ensure page is loaded
                    smoothScrollToElement(targetElement);
                }, 300);
            }
        }
    } catch (error) {
        console.error('Error initializing DocVault scripts:', error);
    }
});