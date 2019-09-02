# flask-restless-transaction

Projeto para habiltar transações utilizando sqlalchemy_continuum.

Arquivo que pode ser utilizado dentro do projeto flask-restless para habilitar o versionamento no banco de dados.

Para utilizar sua tabela principal deve ter uma coluna LOCKED = true.

Também é necessário criar uma tabela de transação contendo as chaves estrangeiras.

Exemplo:
```sql
CREATE TABLE NOME_TABELA_TRANSACTION (
  OID NUMBER NOT NULL,
	ENTITY_OID NUMBER(19,0) NULL, -- Id da tabela principal
	PRODUCT_ID_TR NUMBER NULL,
  CONSTRAINT NOME_TABELA_TR_PK PRIMARY KEY (OID)
 );
```

Obs. Neste código estou usando OID como primary key, futuramente vou deixar configurável por parâmetro.
