import { Meteor } from 'meteor/meteor';
import { Mongo } from 'meteor/mongo';
import { check } from 'meteor/check';

import { Accounts } from 'meteor/accounts-base';
import { Programs } from './programs.js';
import { Observations } from './observations.js';
import { Sessions } from './sessions.js';
import { Groups } from './groups.js';

Meteor.users.deny({
    update() { return true; }
});

// publish users
if (Meteor.isServer) {

    // users
    Meteor.publish('users', function() {
        if (Roles.userIsInRole(Meteor.user(), 'admin')) {
            // publish all users
            return Meteor.users.find({}, {fields: {profile: 1, emails: 1, roles: 1, group: 1,
                                                   maxQueueTime: 1}});
        } else {
            // publish only our user
            return Meteor.users.find({}, {fields: {profile: 1, emails: 1}});
        }
    });

    // TODO: Don't know why this isn't working?
    // // Allow users to only edit their own profiles
    // Meteor.users.deny({
    //  insert() { console.log('insert!'); return true; },
    //  remove() { return true; },
    //  update(userId, doc, fieldNames, modifier) {
    //      console.log('update called!');
    //      // user is not admin
    //      if (!Roles.userIsInRoles(userId, 'admin')) {
    //          // if user tries to edit another use.. Stairway, denied!
    //          if (userId != doc._id) {
    //              return true;
    //          }

    //          // check that they are only changing fields in profile
    //      }
    //      console.log(fieldNames);
    //  }
    // });

}

Meteor.methods({
    'users.insert'(email, groupname, profile) {
        if (Meteor.isServer) {

            // create a new user
            const id = Accounts.createUser({
                email: email,
                profile: profile});

            // user was sucessfully created
            if (id) {

                // find the current group
                group = Groups.findOne({'name': groupname});

                // default values - priority=1, and maxQueueTime=4hours
                priority = 1;
                maxQueueTime = 60*60*4;

                if (group.priority) {
                    priority = group.defaultPriority;
                }

                if (group.maxQueueTime) {
                    maxQueueTime = group.defaultMaxQueueTime;
                }

                // add priority and max queue time from group
                Meteor.users.update(id, {'$set': { 'priority': priority,
                                                   'maxQueueTime': maxQueueTime,
                                                   'group': groupname}});

                // add to user to users group
                Roles.addUsersToRoles(id, ['user']);

                // send enrollment email
                Accounts.sendEnrollmentEmail(id);

            } else {
                CoffeeAlerts.error('Unable to create user...');
            }
        }
    },

    'users.remove'(userId) {
        check(userId, String);

        // check that the user is logged in
        if (! Meteor.userId()) {
            throw new Meteor.Error('not-authorized');
        }

        if (Roles.userIsInRole(Meteor.userId(), 'admin')) {

            // delete all programs (this should also delete obs and sessions)
            Programs.remove({owner: userId});

            // just to be safe, delete all obs and sessions
            Observations.remove({owner: userId});
            Sessions.remove({owner: userId});

            // delete user
            Meteor.users.remove(userId);
        }
    },

    'users.addToRole'(userId, role) {

        // verify
        check(userId, String);

        // check that the user is logged in
        if (! Meteor.userId()) {
            console.log('not-authorized');
            throw new Meteor.Error('not-authorized');
        }

        // check that the current-logged in user is admin
        if (Roles.userIsInRole(Meteor.userId(), 'admin')) {

            // add the user to the role
            Roles.addUsersToRoles(userId, role);

            // remove user from user roles
            Roles.removeUsersFromRoles(userId, 'user');
        }
    },

    'users.removeFromRole'(userId, role) {

        // verify
        check(userId, String);

        // check that the user is logged in
        if (! Meteor.userId()) {
            throw new Meteor.Error('not-authorized');
        }

        // check that the current-logged in user is admin
        if (Roles.userIsInRole(Meteor.userId(), 'admin')) {

            // add the user to the role
            Roles.removeUsersFromRoles(userId, role);

            // add user to 'users'
            Roles.addUsersToRoles(userId, 'user');
        }
    },

    'users.checkPassword'(userId, digest) {
        if (Meteor.isServer) {
            check(digest, Object);

            if (userId) {
                // find the user
                user = Meteor.users.findOne(userId);
                if (user) {
                    const result = Accounts._checkPassword(user, digest);
                    return (result.userId == userId) && (result.error == undefined);
                }
                else {
                    return false;
                }
            } else {
                return false;
            }
        }
        return false;
    },

    'users.setPassword'(userId, password, callback) {
        if (Meteor.isServer) {
            check(password, String);

            if (userId) {
                // only admins can change other users passwords, or user changes their own
                if (Roles.userIsInRole(Meteor.user(), 'admin') || (Meteor.userId() == userId)) {

                    // change the password
                    Accounts.setPassword(userId, password, callback);
                }
            }
        }
    }
});
