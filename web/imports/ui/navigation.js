import './navigation.html'

Template.navigation.events({
    'click .logout'(event) {
	event.preventDefault();
	Meteor.logout();
	Router.go('/')
    }
});
