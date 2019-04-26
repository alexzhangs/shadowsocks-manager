# shadowsocks-manager

A Shadowsocks management tool for multi user and traffic control,
support multi node, LDAP support is in future plan.
Writen in Python, base on Django/DjangoRESTFramework and SQLite.

It relies on Shadowsocks Multi-User API, which is only
supported by Shadowsocks libev and Python version.

## Differences from shadowsocks/shadowsocks-manager

Do's and Don'ts of this repo:

* Don't: Handle self-serviced user registration.
* Do: Manage user with admin and/or sync user from LDAP server.

* Don't: Handle bill or payment.
* Do: Serve as a nonprofit business model.

* Don't: Run additional agent on each Shadowsocks server.
* Do: Be installed and run on a single master server.

## Dependences

```
shadowsocks-manager (github)
├── [aws-ec2-ses] (github optional)
└── shadowsocks-manager-ldap (github)
```
