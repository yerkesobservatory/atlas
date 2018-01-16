// setup the main template (with header and footers)
Router.configure({
    layoutTemplate: 'main',
    notFoundTemplate: "notfound",
    loadingTemplate: "loading"
});

// fix some bizarre error
Router.onBeforeAction(function() {
    CoffeeAlerts.clearSeen();
    this.next();
});

// configure route for sign in
// we redirect to observations if the user is already signed in
AccountsTemplates.configureRoute('signIn', {
    name: 'signin',
    path: '/login',
    template: 'login',
    layoutTemplate: 'empty',
    redirect: function() {
	var uswer = Meteor.user();
	if (user)
      //this.redirect('/home');
      Router.go('/');
    }
});

// create page routings for other pages
Router.route('/', 'home');
Router.route('/home');
Router.route('/newObservation');
Router.route('/observations');
Router.route('/sessions');
Router.route('/programs');
Router.route('/admin', {
    onBeforeAction: function () {
	if (Roles.userIsInRole(Meteor.userId(), 'admin')) {
	    this.next();
	} else {
	    this.redirect('home');
	}
    }});
Router.route('/control');
Router.route('/forgot', {
    path: '/forgot',
    template: 'forgotPassword'
});
Router.route('reset', {
    path: '/reset/:token',
    template: 'resetPassword'
});

Router.onBeforeAction('dataNotFound');

// require sign in for every page except registration/reset
Router.plugin('ensureSignedIn', {except: ['forgot', 'reset']});
