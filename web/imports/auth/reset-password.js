import './reset-password.html';

import { Accounts } from 'meteor/accounts-base';

// called when "reset password" button is pressed
Template.forgotPassword.events({
    'submit .forgotPassword'(event) {
        // prevent default submission
        event.preventDefault();

        // clear 'success' formatting from form
        $('.new-program').find('.form-group').removeClass('has-success');

        // extract values
        const target = event.target;
        const email = target.email.value.toLowerCase();

        // attempt to send email
        Accounts.forgotPassword({email: email}, function(error) {
            if (error) {
                if (error.message === 'User not found [403]') {
                    CoffeeAlerts.error('Username not found.');
                } else {
                    CoffeeAlerts.error(error.message);
                }
            } else {
                CoffeeAlerts.success('Your password has been reset. Please check your email for a link to set a new password');
            }
        });
        Router.go('home');
    }
});


// called when "change password" button is pressed
Template.resetPassword.events({
    'submit .resetPassword'(event) {
        // prevent default submission
        event.preventDefault();

        // clear 'success' formatting from form
        $('.resetPassword').find('.form-group').removeClass('has-success');

        // extract values
        const target = event.target;
        const password = target.password.value;
        const passwordRepeat = target.passwordRepeat.value;

	// if passwords do not match
        if (password != passwordRepeat) {
            return;
        }

	// get token fro mURL
	const token = Router.current().params.token;

        // attempt to send email
        Accounts.resetPassword(token, password, function(error) {
            if (error) {
                if (error.message === 'User not found [403]') {
                    CoffeeAlerts.error('Username not found.');
                } else {
                    CoffeeAlerts.error(error.reason);
                }
            } else {
                CoffeeAlerts.success('Password successfully changed. You are now logged in.');
            }
        });

        Router.go('/');
    }
});


// build rules for form validation
Template.resetPassword.onRendered(function() {
    $( '.resetPassword' ).validate({
        errorClass: 'text-danger',
        errorElement: 'p',
        highlight: function(element, errorClass) {
            $(element.form).find('#form-'+element.id).removeClass('has-success');
            $(element.form).find('#form-'+element.id).addClass('has-error');
        },
        unhighlight: function(element, errorClass) {
            $(element.form).find('#form-'+element.id).removeClass('has-error');
            $(element.form).find('#form-'+element.id).addClass('has-success');
        },
        rules: {
            password: {
                required: true,
                minlength: 12,
                maxlength: 128},
            passwordRepeat: {
                required: true,
                minlength: 12,
                maxlength: 128,
                equalTo: "#password"},
        },
        messages: {
            password: {
                required: "You have to choose a new password!",
                minlength: "Your password has to be atleast 12 characters",
                maxlength: "For the purpose of sanity, we restrict passwords to 128 characters.",
            },
            passwordRepeat: {
                equalTo: "Oops, your passwords do not match!"
            }
        }
    });
});

// build rules for form validation
Template.forgotPassword.onRendered(function() {
    $( '.forgotPassword' ).validate({
        errorClass: 'text-danger',
        errorElement: 'p',
        highlight: function(element, errorClass) {
            $(element.form).find('#form-'+element.id).removeClass('has-success');
            $(element.form).find('#form-'+element.id).addClass('has-error');
        },
        unhighlight: function(element, errorClass) {
            $(element.form).find('#form-'+element.id).removeClass('has-error');
            $(element.form).find('#form-'+element.id).addClass('has-success');
        },
        rules: {
            email: {
                required: true,
                minlength: 4,
                maxlength: 32
            },
        },
    });
});
