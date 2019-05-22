grammar tql;

sequence
    : eu_declaration_list
      NEWLINE
      interaction *
      SEMICOLON
    ;

interaction
    : event_list NEWLINE
    ;

eu_declaration_list
    : eu_decl  //+
    ;

event_list
    : event //+
    ;

eu_decl
    :               LBRACKET
      eu_type=      IDENTIFIER?
      var_name=     declarable_identifier
                    tags?
                    RBRACKET
    ;

tags
    :               LPAREN
                    tag (COMMA tag)*
                    RPAREN
    ;

tag
    : tag_key=      IDENTIFIER
                    EQUAL_SIGN
      tag_value=    right_value
    ;

right_value
    : (IDENTIFIER|literal)
    ;

event
    :               ASTERISK
      var_name=     declarable_identifier
                    (COLON event_type=IDENTIFIER)?
                    (PER status=IDENTIFIER)?
                    tags?
    ;

declarable_identifier
    : identifier_declaration
    | IDENTIFIER
    ;

identifier_declaration
    : BANG
      IDENTIFIER
    ;

literal
    : FLOAT
    | INTEGER
    | STRING
    ;

FLOAT
    : [0-9]+[.][0-9]*
    ;

INTEGER
    : [0-9]+
    ;

STRING
    : '"'
      ((~["\\\r\n])|('\\' ["\\nr]))*
      '"'
    ;

IDENTIFIER
    :   IdentifierNondigit
        (   IdentifierNondigit
        |   Digit
        )*
    ;

fragment
Digit
    :   [0-9]
    ;
fragment
IdentifierNondigit
    :   [a-zA-Z_]
    ;

ASTERISK
    : '*'
    ;

LPAREN
    : '('
    ;
RPAREN
    : ')'
    ;

LBRACKET
    : '['
    ;
RBRACKET
    : ']'
    ;

LBRACE
    : '{'
    ;
RBRACE
    : '}'
    ;

EQUAL_SIGN
    : '='
    ;

COMMA
    : ','
    ;

COLON
    : ':'
    ;

SEMICOLON
    : ';'
    ;

PIPE
    : '|'

    ;
PER
    : '/'
    ;

BANG
    : '!'
    ;

NEWLINE
    : '\n'
    ;

Whitespace
    :   [ \t]+
        -> skip
    ;