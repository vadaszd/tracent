grammar tql;

eu_decl
    :               LBRACKET
      eu_type=      IDENTIFIER?
      var_name=     declarable_identifier
                    tags?
                    event*
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
    :               ASTEERISK
      var_name=     declarable_identifier
                    (PIPE event_type=right_value)
                    (PER status=right_value)
                    tags
    ;

declarable_identifier
    : identifier_declaration
    | IDENTIFIER
    ;

identifier_declaration
    : BANG
      IDENTIFIER
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

PIPE
    : '|'

    ;
PER
    : '/'
    ;

BANG
    : '!'
    ;