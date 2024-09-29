create table "user"
(
    id       serial       not null primary key,
    username varchar(80)  not null unique,
    password varchar(200) not null
);
