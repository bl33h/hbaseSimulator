from pydantic import BaseModel
from typing import Union
import os
import json
import time
import shutil

class Table(BaseModel):
    """
    Clase que guarda las configuraciones de una tabla
    """
    enabled: bool = True
    name : str
    column_families: dict[str, dict[str, str]]

    """"
    enabled: true,
    "name": "table1",
    "column_families": {
        "cf1": {
            "version": "1",
            ...
        },
    """
    def write_to_memory(self):
        """
        Guarda el contenido de la tabla en un archivo config.json
        """
        # if not exists create folder table/{self.name}
        
        if not os.path.exists(f"tables/{self.name}"):
            os.makedirs(f"tables/{self.name}")

        # write the table to a file config.json
        with open(f"tables/{self.name}/config.json", "w") as f:
            json.dump(self.dict(), f)

        # create region
        if not os.path.exists(f"tables/{self.name}/regions"):
            os.makedirs(f"tables/{self.name}/regions")

        if not os.path.exists(f"tables/{self.name}/regions/region1"):
            os.makedirs(f"tables/{self.name}/regions/region1")

    #funciones de la clase
    def disable(self):
        """
        Deshabilitar la tabla
        """
        self.enabled = False
        self.write_to_memory()

    def enable(self):
        """
        Habilitar la tabla
        """
        self.enabled = True
        self.write_to_memory()

    def describe(self):
        """ Retorna una descripción detallada de las columnas de la tabla al estilo de HBase. """
        status = 'enable' if self.enabled else 'disable'
        header = f"Table {self.name} is {status}\n{self.name}\nCOLUMN FAMILIES DESCRIPTION"
        description = []

        for name, props in self.column_families.items():
            cf_description = f"{{NAME => '{name}', "
            cf_description += ', '.join([f"{key} => '{value}'" for key, value in props.items()])
            cf_description += "}"
            description.append(cf_description)

        return f"{header}\n" + '\n'.join(description)
    
    def alter(self, column_family: str, version: str):
        """
        Parte de las funcionalidades del comando 'ALTER TABLE' de HBase.
        Alterar la tabla para cambiar la versión de un column family.
        """
        self.column_families[column_family]['version'] = version
        self.write_to_memory()

    def drop_column_family(self, column_family: str):
        """
        Parte de las funcionalidades del comando 'ALTER TABLE' de HBase.
        Eliminar un column family de la tabla.
        """
        del self.column_families[column_family]
        self.write_to_memory()

    def add_column_family(self, column_family: str, version: str):
        """
        Agregar un column family a la tabla
        """
        self.column_families[column_family] = {'version': version}
        self.write_to_memory()

    def drop(self):
        """
        Hace un drop de la tabla
        """

        if os.path.exists(f"tables/{self.name}"):
            shutil.rmtree(f"tables/{self.name}")

class HFile(BaseModel):
    """
    Clase que simula un archivo HFile
    """
    table: str
    region: str = "region1"
    rows: dict[int, dict[str, dict[str, dict[str, str]]]] = {}
    versions: int = 1

    """
    rows = 
    {
        "1": {
            "column_fam_1": {
                "column_qualifier": {
                    "timestamp": "1",
                }
            },
            "column_fam_2": {
                "column_qualifier": {
                    "timestamp": "1",
                }
            }
        },
    }
    """

    def __init__(self, table: str, region: str = "region1", versions: int = 1):
        """
        Inicializa la clase
        :param table: Nombre de la tabla
        :param region: Nombre de la región
        """
        super().__init__(table=table, region=region)

        self.table = table
        self.region = region
        self.versions = int(versions)
        
        path = f"tables/{self.table}/regions/{self.region}"

        # Verificar si existe el archivo hfile.json
        if os.path.exists(f"{path}/hfile.json"):
            print("hfile.json exists")
            with open(f"{path}/hfile.json", "r") as f:
                self.rows = json.load(f)
        else:
            self.rows = {}
            # create hfie.json
            with open(f"{path}/hfile.json", "w") as f:
                json.dump(self.rows, f)

    def write_to_memory(self):
        """
        Guarda el contenido de la tabla en un archivo hfile.json
        """
        path = f"tables/{self.table}/regions/{self.region}"
        # order rows by row number
        self.rows = dict(sorted(self.rows.items()))
        with open(f"{path}/hfile.json", "w") as f:
            json.dump(self.rows, f)

    def put(self, row: int, column_family: str, column_qualifier: str, value: Union[str, int, float]):
        """
        Inserta un valor en la tabla
        :param row: Identificador de la fila
        :param column_family: Nombre de la familia de columnas
        :param column_qualifier: Nombre de la columna
        :param value: Valor a insertar
        """

        ts = str(int(time.time()))

        if row not in self.rows:
            self.rows[row] = {}
        if column_family not in self.rows[row]:
            self.rows[row][column_family] = {}
        if column_qualifier not in self.rows[row][column_family]:
            self.rows[row][column_family][column_qualifier] = {}
        self.rows[row][column_family][column_qualifier][ts] = value

        # Verificar si se excede el número de versiones
        if len(self.rows[row][column_family][column_qualifier]) > self.versions:
            # delete the oldest version
            ts_to_delete = min(self.rows[row][column_family][column_qualifier])
            print(f"Deleting {ts_to_delete}")
            del self.rows[row][column_family][column_qualifier][ts_to_delete]

        self.write_to_memory()

    def get(self, row: int) -> dict[str, dict[str, dict[str, str]]]:
        """
        Obtiene una fila de la tabla
        :param row: Identificador de la fila
        :return: Diccionario con la fila
        """

        return self.rows[row]
    
    def delete(self, row: int, column_family: str, column_qualifier: str, timestamp: str):
        """
        Elimina un valor de la tabla
        :param row: Identificador de la fila
        :param column_family: Nombre de la familia de columnas
        :param column_qualifier: Nombre de la columna
        :param timestamp: Timestamp del valor a eliminar
        """
        del self.rows[row][column_family][column_qualifier][timestamp]
        self.write_to_memory()

    def delete_all(self, row: int):
        """
        Elimina una fila de la tabla
        :param row: Identificador de la fila
        """
        del self.rows[row]
        self.write_to_memory()

    def scan(self) -> dict[int, dict[str, dict[str, dict[str, str]]]]:
        """
        Escanea la tabla
        :return: Diccionario con las filas de la tabla
        """
        return self.rows
    
    def truncate(self):
        """
        Elimina todas las filas de la tabla
        """
        self.rows = {}
        self.write_to_memory()

    def update_changes(self, table: Table):
        """
        Actualiza los cambios de la tabla
        """

        # Si en el hfile hay column families que no están en la tabla, eliminarlas
        rows_to_delete = []
        for row in self.rows:
            for column_family in self.rows[row]:
                if column_family not in table.column_families:
                    rows_to_delete.append(row)

        for row in rows_to_delete:
            del self.rows[row]

        self.write_to_memory()
