/**
 * Set organization slug in localStorage for testing avatar functionality
 * 
 * Usage:
 * 1. Open browser console on http://localhost:4200
 * 2. Paste this script and run it
 * 3. Refresh the page
 * 
 * The chatbot will now fetch the avatar for 'test-org' organization
 */

console.log('Setting organization slug for testing...');
localStorage.setItem('ace_organization_slug', 'test-org');
console.log('✅ Organization slug set to: test-org');
console.log('Refresh the page to load the avatar');
