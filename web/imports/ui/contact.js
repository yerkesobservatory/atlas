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
/*
Template.contacts_admins.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
});

Template.contacts_users.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
});

Template.chatAction.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
});*/
/*
Template.contact.helpers({
  settings: function() {
    return {
      collection: Meteor.users.find({newMessage: 1}),
        showRowCount: true,
        showNavigationRowsPerPage: false,
      fields: [
        {key:'profile.firstName', label:'First'},
        {key:'profile.lastName', label:'Last'},
        {key:'group', label:'Group'},
        {key:'roles', label:'Role'},
        {key:'newMessage', label:'Status',
    		fn: function(value, object, key) {
    			var status = Meteor.user().newMessage
    			if (status) {
    				if (status.includes(this.userId)) {
    					return 'new!'
    				}
    			} 
    			return 'No new message'
    		}},
        {label: '',
                 tmpl: Template.chatAction
                }]
    }
  },
});*/


Template.contact.helpers({
	hasNewMessage: function() {
		if (Meteor.users.find({newMessageTo: Meteor.userId()}) != null) {
			return true;
		}
		return false;
	},
	newMessageSettings: function() {
		return {
			collection: Meteor.users.find({'newMessageTo': Meteor.userId()}),
        	showRowCount: true,
        	showNavigationRowsPerPage: false,
      		fields: [
        		{key:'profile.firstName', label:'First'},
        		{key:'profile.lastName', label:'Last'},
        		{key:'group', label:'Group'},
        		{label: '',
                 tmpl: Template.chatAction
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
            window.location.href = 'message' + '/'+roomid+'/'+this.profile.firstName+' '+this.profile.lastName+'/'+this._id;
        }
    },
});

Template.online.helpers({ 
	isOnLine: function () {
        return this.status.online
    },
});

