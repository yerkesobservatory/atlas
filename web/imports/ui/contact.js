import './contact.html'

import { Meteor } from 'meteor/meteor';
import { Tracker } from 'meteor/tracker';

import { Programs } from '../api/programs.js';
import { Groups } from '../api/groups.js';
import $ from 'jquery';
import {SimpleChat} from 'meteor/cesarve:simple-chat/config'
import { UserStatus } from 'meteor/mizzao:user-status';

Template.contact.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
    Meteor.subscribe('userStatus');
    console.log(Meteor.user());
});


Template.contact.helpers({
	hasNewMessage: function() {
		if (Meteor.users.find({roles: Meteor.userId()}) != null) {
			return true;
		}
		return false;
	},
	newMessageSettings: function() {
		return {
			collection: Meteor.users.find({roles: Meteor.userId()}),
        	showRowCount: true,
        	showNavigationRowsPerPage: false,
      		fields: [
        		{key:'profile', label:'Name',
        		fn: function(value, object, key){
        			return object.profile.firstName +' ' +object.profile.lastName;
        		} },
        		{key:'group', label:'Group'},
        		{label: '',
                 tmpl: Template.newMessage
                }]
    	}
	},
	userAdmins: function() { 
      			return Meteor.users.find({roles:'admin'});
      		},
    userUsers: function() { 
      			return Meteor.users.find({roles:'user'});
      		},
  	settings: function() {
    return {
        showRowCount: true,
        showNavigationRowsPerPage: false,
      	fields: [
        {key:'profile.firstName', label:'First'},
        {key:'profile.lastName', label:'Last'},
        {key:'group', label:'Group'},
        {key:'', label:'Status', tmpl: Template.online,
    	},
        {label: '',
                 tmpl: Template.chatAction
                }]
    }
  },
});


Template.contact.events({
	'click .reactive-table tbody tr': 
	function (event) {
        event.preventDefault();
        // checks if the actual clicked element has the class `delete`
        if (event.target.id = ('message')) {
        	var roomid = '';
        	if ( this._id <= Meteor.userId()){
        		roomid = this._id + Meteor.userId();
        	} else {
        		roomid = Meteor.userId() + this._id;
        	}
        	//console.log('before newMessageTo');
        	Meteor.call('users.newMessageTo', Meteor.userId(), this._id);
        	var othername = this.profile.firstName +' '+ this.profile.lastName
        	var url = 'message' + '/'+roomid+'/'+othername+'/'+this._id
        	if (this.status.online != true){
        		var to = this.emails[0];
        		var subject = 'New Message from '+othername+ ' in Stone Edge Observatory. '
        		var text = subject + 'Click here to view '+'https://queue.stoneedgeobservatory.com/'+url;
        		Meteor.call('sendEmail',to,subject,text);
        	}
        	Meteor.call('users.newMessageRead', Meteor.userId(), this._id);
        	//console.log('after newMessageTo');
        	//console.log(Meteor.user());
            window.location.href = url;
        }
    },
});

Template.online.helpers({ 
	isOnLine: function () {
        return this.status.online
    },
});

