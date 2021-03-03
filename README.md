# monitor-memos
A command line utility for monitoring memo's stored in the bitcoin cash blockchain using the 'memo' protocol.

While there were several similar tools out in the wild, they all suffered from being a little old and relying on out of date
Python versions or deprecated javascript libraries. Given how simple the memo protocol is, it seemed easier to create
a purpose built library.

The original (and primary) intent of this was to create a simple command line utility for monitoring and grabbing
recent memos posted to the blockchain so that they could be included in a sidebar of anther website somewhat like
the numerous twitter plugins for things like Wordpress.

This is not currently a general purpose API for accessing the memo protocol and is likely to remain a purpose built tool with
somewhat limited flexibility.

