from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Sequence
from sqlalchemy.dialects.oracle import NUMBER
from sqlalchemy_continuum import count_versions
from sqlalchemy.orm.session import object_session


class CustomTransaction:
    """Classe responsável por realizar o versionamento dos dados no banco
    utilizando a biblioteca sqlalchemy_continuum.

    Para fixar (lock) uma versão de uma tabela levando em consideração seus relacionamentos,
    basta colocar a coluna `LOCKED` como True

    """
    def __init__(self, session, old_instance, instance, deep):
        self.Base = declarative_base()
        self.metadata = self.Base.metadata
        self.session = session
        self.instance = instance
        self.old_instance = old_instance
        self.deep = deep

    def save_or_update_transaction(self):
        f_keys = self.get_f_keys()
        if hasattr(self.instance, 'locked'):
            if self.instance.locked:
                model_factory = self.factory_table_transaction(f_keys)
                transaction_model = self.get_transaction_by_id(model_factory)
                if transaction_model:
                    model_factory_instance = transaction_model
                else:
                    model_factory_instance = model_factory()
                model_factory_instance.entity_oid = self.instance.oid
                transaction_id = self.instance.versions[count_versions(self.instance) - 1]. \
                    transaction.id
                for f_key in f_keys:
                    f_key_oid = f_key + '_oid'
                    if not self.old_instance or \
                            (self.old_instance and
                             getattr(self.old_instance, f_key_oid) != getattr(self.instance, f_key_oid)):
                        if not getattr(self.instance, f_key_oid):
                            setattr(model_factory_instance, f_key + '_id_tr', None)
                        else:
                            setattr(model_factory_instance, f_key + '_id_tr', transaction_id)
                if not transaction_model:
                    self.session.add(model_factory_instance)
                self.session.commit()

    def factory_table_transaction(self, f_keys):
        check = self._check_existing_table_in_metadata(self.generate_table_name())
        if check:
            self.metadata.clear()
        table_model = {
            '__tablename__': self.generate_table_name(),
            'oid': Column(NUMBER(), Sequence(self.generate_sequence_name()), primary_key=True),
            'entity_oid': Column(NUMBER(), primary_key=True)
        }
        for f_key in f_keys:
            table_model.update({f_key + '_id_tr': Column(NUMBER())})
        new_class = type(self.generate_class_name(), (self.Base,), table_model)
        return new_class

    def _check_existing_table_in_metadata(self, table):
        for _t in self.metadata.tables:
            if str(_t) == table:
                return True
        return False

    def generate_table_name(self):
        return self.instance.__tablename__ + '_transaction'

    def generate_sequence_name(self):
        return self.instance.__tablename__ + '_tr_seq'

    def generate_class_name(self):
        return self.instance.__tablename__.replace('s', '').capitalize() + 'Transaction'

    def get_f_keys(self):
        return list(filter(lambda x: x is not 'versions' and not isinstance(getattr(self.instance, x), list),
                           self.deep.keys()))

    def get_transaction_by_id(self, model):
        if not self.session:
            self.session = object_session(self.instance)
        return self.session.query(model).filter(model.entity_oid == self.instance.oid).first()

    def revert_sqlalchemy_continuum_locked(self):
        if not hasattr(self.instance, 'locked') or not hasattr(self.instance, '__versioned__'):
            return
        if not self.instance.locked:
            return
        properties_reverted = {}
        f_keys = self.get_f_keys()
        model_factory = self.factory_table_transaction(f_keys)
        transaction_model = self.get_transaction_by_id(model_factory)
        if not transaction_model:
            return
        not_null_columns = list(filter(lambda l_column: l_column is not '_sa_instance_state'
                                       and 'tr' in l_column.lower()
                                       and getattr(transaction_model, l_column),
                                       transaction_model.__dict__.keys()))
        all_versions = self.instance.versions.all()
        for column in not_null_columns:
            id_transaction = getattr(transaction_model, column)
            if id_transaction:
                try:
                    version_obj = list(filter(lambda x: x.transaction_id == id_transaction, all_versions))
                    property_mapped_name = self.get_name_column_fk_mapped_by_transaction(column)
                    version_obj[0].revert(relations=[property_mapped_name])
                    properties_reverted[property_mapped_name] = getattr(self.instance, property_mapped_name)
                except Exception as e:
                    pass
        self.instance.versions[len(all_versions)-1].revert()
        for key, value in properties_reverted.items():
            setattr(self.instance, key, value)

    def get_name_column_fk_mapped_by_transaction(self, column_transaction):
        column_transaction = column_transaction.split('_id')[0]
        if column_transaction[len(column_transaction)-1] == 's':
            column_transaction.replace(column_transaction[len(column_transaction) - 1])
        return column_transaction






