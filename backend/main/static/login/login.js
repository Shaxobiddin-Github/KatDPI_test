
        // Role selection handler
        document.querySelectorAll('.role-card').forEach(card => {
            card.addEventListener('click', function() {
                // Remove active class from all cards
                document.querySelectorAll('.role-card').forEach(c => c.classList.remove('active'));
                
                // Add active class to clicked card
                this.classList.add('active');
                
                // Get selected role
                const role = this.getAttribute('data-role');
                document.getElementById('selectedRole').value = role;
                
                // Toggle fields with animation
                toggleFields(role);
                
                // Update login button text
                updateLoginText(role);
            });
        });
        
        function toggleFields(role) {
            const accessFields = document.getElementById('access-fields');
            const userFields = document.getElementById('user-fields');
            if (['student', 'tutor', 'employee'].includes(role)) {
                userFields.style.display = 'none';
                accessFields.style.display = 'block';
                setTimeout(() => {
                    accessFields.classList.add('field-transition');
                }, 10);
            } else {
                accessFields.style.display = 'none';
                userFields.style.display = 'block';
                setTimeout(() => {
                    userFields.classList.add('field-transition');
                }, 10);
            }
        }
        
        function updateLoginText(role) {
            const loginText = document.getElementById('loginText');
            const texts = {
                'student': '🎓 Talaba sifatida kirish',
                'tutor': '🧑‍🏫 Tutor sifatida kirish',
                'employee': '💼 Xodim sifatida kirish',
                'teacher': '👨‍🏫 O\'qituvchi sifatida kirish',
                'controller': '⚙️ Controller sifatida kirish'
            };
            loginText.textContent = texts[role] || 'Kirish';
        }
        
        // Form validation and submission
        document.getElementById('loginForm').addEventListener('submit', function(e) {
            const role = document.getElementById('selectedRole').value;
            const accessCode = document.getElementById('access-code').value;
            const username = document.getElementById('username').value;
            if (['student', 'tutor', 'employee'].includes(role) && !accessCode.trim()) {
                e.preventDefault();
                showError('Access kod kiritish majburiy!');
                return;
            }
            if (['teacher', 'controller'].includes(role)) {
                if (!username.trim()) {
                    e.preventDefault();
                    showError('Username kiritish majburiy!');
                    return;
                }
                const password = document.getElementById('password').value;
                if (!password.trim()) {
                    e.preventDefault();
                    showError('Parol kiritish majburiy!');
                    return;
                }
            }
            // Add loading state
            const btn = document.querySelector('.btn-login');
            btn.innerHTML = '⏳ Kirilmoqda...';
            btn.disabled = true;
        });
        
        function showError(message) {
            // Remove existing error if any
            const existingError = document.querySelector('.custom-error');
            if (existingError) {
                existingError.remove();
            }
            
            // Create new error
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger custom-error';
            errorDiv.innerHTML = `<strong>⚠️ Xatolik:</strong> ${message}`;
            
            // Insert before form
            const form = document.getElementById('loginForm');
            form.parentNode.insertBefore(errorDiv, form);
            
            // Auto remove after 5 seconds
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.remove();
                }
            }, 5000);
        }
        
        // Auto-format access code (only numbers, max 5 digits)
        document.getElementById('access-code').addEventListener('input', function(e) {
            this.value = this.value.replace(/[^0-9]/g, '').slice(0, 5);
        });
        
        // Enhanced focus effects
        document.querySelectorAll('.form-control').forEach(input => {
            input.addEventListener('focus', function() {
                this.parentNode.style.transform = 'scale(1.02)';
            });
            
            input.addEventListener('blur', function() {
                this.parentNode.style.transform = 'scale(1)';
            });
        });
        
        // Initialize on page load
        window.addEventListener('load', function() {
            updateLoginText('student');
            
            // Add entrance animation delay
            setTimeout(() => {
                document.querySelector('.login-box').style.opacity = '1';
            }, 100);
        });
        
        // Keyboard navigation for role cards
        document.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                const activeCard = document.querySelector('.role-card.active');
                const cards = Array.from(document.querySelectorAll('.role-card'));
                const currentIndex = cards.indexOf(activeCard);
                
                let newIndex;
                if (e.key === 'ArrowLeft') {
                    newIndex = currentIndex > 0 ? currentIndex - 1 : cards.length - 1;
                } else {
                    newIndex = currentIndex < cards.length - 1 ? currentIndex + 1 : 0;
                }
                
                cards[newIndex].click();
                e.preventDefault();
            }
        });
