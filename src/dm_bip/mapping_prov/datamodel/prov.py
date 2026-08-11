from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.11.0"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'mapping_prov_schema',
     'default_range': 'string',
     'description': 'Extension of the PROV LinkML schema '
                    '(https://github.com/diatomsRcool/prov-schema) adding the '
                    'dbGaP data granularity called for in '
                    'https://github.com/linkml/dm-bip/issues/352: studies, '
                    'datasets (pht accessions), and variables (phv accessions), '
                    'with containment expressed structurally (variables within '
                    'datasets, datasets within studies) so that '
                    'study/dataset/variable alignment survives downstream.',
     'id': 'https://w3id.org/dm-bip/mapping-prov-schema',
     'imports': ['linkml:types',
                 'https://raw.githubusercontent.com/diatomsRcool/prov-schema/main/src/prov_schema/schema/prov_schema'],
     'license': 'MIT',
     'name': 'mapping_prov_schema',
     'prefixes': {'bdchm': {'prefix_prefix': 'bdchm',
                            'prefix_reference': 'https://w3id.org/bdchm/'},
                  'dbgap': {'prefix_prefix': 'dbgap',
                            'prefix_reference': 'https://identifiers.org/dbgap/'},
                  'dmcprov': {'prefix_prefix': 'dmcprov',
                              'prefix_reference': 'https://w3id.org/dm-bip/mapping-prov/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'mapping_prov_schema': {'prefix_prefix': 'mapping_prov_schema',
                                          'prefix_reference': 'https://w3id.org/dm-bip/mapping-prov-schema/'},
                  'prov': {'prefix_prefix': 'prov',
                           'prefix_reference': 'http://www.w3.org/ns/prov#'}},
     'see_also': ['https://github.com/linkml/dm-bip/issues/352',
                  'https://www.w3.org/TR/prov-o/'],
     'source_file': 'src/dm_bip/mapping_prov/schema/mapping_prov_schema.yaml',
     'title': 'DM-BIP Mapping Provenance Schema'} )


class NamedThing(ConfiguredBaseModel):
    """
    A generic grouping for any identifiable entity
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True, 'from_schema': 'https://w3id.org/prov-schema'})

    id: str = Field(default=..., description="""A unique identifier for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    name: Optional[str] = Field(default=None, description="""A human-readable name for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    description: Optional[str] = Field(default=None, description="""A human-readable description for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })


class Entity(NamedThing):
    """
    An entity is a physical, digital, conceptual, or other kind of thing with some fixed aspects; entities may be real or imaginary.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'prov:Entity', 'from_schema': 'https://w3id.org/prov-schema'})

    attributed_to: Optional[str] = Field(default=None, description="""Attribution is the ascribing of an entity to an agent""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasAttributedTo'} })
    derived_from: Optional[list[str]] = Field(default=None, description="""A derivation is a transformation of an entity into another, an update of an entity resulting in a new one, or the construction of a new entity based on a pre-existing entity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasDerivedFrom'} })
    generated_by: Optional[str] = Field(default=None, description="""Generation is the completion of production of a new entity by an activity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasGeneratedBy'} })
    id: str = Field(default=..., description="""A unique identifier for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    name: Optional[str] = Field(default=None, description="""A human-readable name for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    description: Optional[str] = Field(default=None, description="""A human-readable description for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })


class File(Entity):
    """
    A file is a named collection of data stored on a file system
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'bdchm:File', 'from_schema': 'https://w3id.org/prov-schema'})

    attributed_to: Optional[str] = Field(default=None, description="""Attribution is the ascribing of an entity to an agent""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasAttributedTo'} })
    derived_from: Optional[list[str]] = Field(default=None, description="""A derivation is a transformation of an entity into another, an update of an entity resulting in a new one, or the construction of a new entity based on a pre-existing entity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasDerivedFrom'} })
    generated_by: Optional[str] = Field(default=None, description="""Generation is the completion of production of a new entity by an activity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasGeneratedBy'} })
    id: str = Field(default=..., description="""A unique identifier for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    name: Optional[str] = Field(default=None, description="""A human-readable name for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    description: Optional[str] = Field(default=None, description="""A human-readable description for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })


class DataObject(Entity):
    """
    A data object is a discrete unit of data with defined structure or content
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/prov-schema'})

    in_file: Optional[str] = Field(default=None, description="""The file that contains this data object""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataObject']} })
    attributed_to: Optional[str] = Field(default=None, description="""Attribution is the ascribing of an entity to an agent""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasAttributedTo'} })
    derived_from: Optional[list[str]] = Field(default=None, description="""A derivation is a transformation of an entity into another, an update of an entity resulting in a new one, or the construction of a new entity based on a pre-existing entity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasDerivedFrom'} })
    generated_by: Optional[str] = Field(default=None, description="""Generation is the completion of production of a new entity by an activity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasGeneratedBy'} })
    id: str = Field(default=..., description="""A unique identifier for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    name: Optional[str] = Field(default=None, description="""A human-readable name for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    description: Optional[str] = Field(default=None, description="""A human-readable description for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })


class TransformationSpec(Entity):
    """
    A specification that defines how data is transformed from one form to another
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/prov-schema'})

    attributed_to: Optional[str] = Field(default=None, description="""Attribution is the ascribing of an entity to an agent""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasAttributedTo'} })
    derived_from: Optional[list[str]] = Field(default=None, description="""A derivation is a transformation of an entity into another, an update of an entity resulting in a new one, or the construction of a new entity based on a pre-existing entity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasDerivedFrom'} })
    generated_by: Optional[str] = Field(default=None, description="""Generation is the completion of production of a new entity by an activity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasGeneratedBy'} })
    id: str = Field(default=..., description="""A unique identifier for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    name: Optional[str] = Field(default=None, description="""A human-readable name for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    description: Optional[str] = Field(default=None, description="""A human-readable description for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })


class Activity(NamedThing):
    """
    An activity is something that occurs over a period of time and acts upon or with entities; it may include consuming, processing, transforming, modifying, relocating, using, or generating entities.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'prov:Activity', 'from_schema': 'https://w3id.org/prov-schema'})

    started_at_time: Optional[datetime ] = Field(default=None, description="""The time at which the activity started""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity'], 'slot_uri': 'prov:startedAtTime'} })
    ended_at_time: Optional[datetime ] = Field(default=None, description="""The time at which the activity ended""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity'], 'slot_uri': 'prov:endedAtTime'} })
    has_input: Optional[list[str]] = Field(default=None, description="""An entity that is used as input to an activity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity'], 'slot_uri': 'prov:used'} })
    has_output: Optional[list[str]] = Field(default=None, description="""An entity that is generated as output by an activity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity']} })
    associated_with: Optional[str] = Field(default=None, description="""An agent that is associated with an activity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity'], 'slot_uri': 'prov:wasAssociatedWith'} })
    id: str = Field(default=..., description="""A unique identifier for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    name: Optional[str] = Field(default=None, description="""A human-readable name for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    description: Optional[str] = Field(default=None, description="""A human-readable description for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })


class Agent(NamedThing):
    """
    An agent is something that bears some form of responsibility for an activity taking place, for the existence of an entity, or for another agent's activity.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'prov:Agent', 'from_schema': 'https://w3id.org/prov-schema'})

    id: str = Field(default=..., description="""A unique identifier for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    name: Optional[str] = Field(default=None, description="""A human-readable name for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    description: Optional[str] = Field(default=None, description="""A human-readable description for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })


class Variable(Entity):
    """
    A dbGaP variable (phv accession): a single column within a dbGaP dataset
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dm-bip/mapping-prov-schema'})

    attributed_to: Optional[str] = Field(default=None, description="""Attribution is the ascribing of an entity to an agent""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasAttributedTo'} })
    derived_from: Optional[list[str]] = Field(default=None, description="""A derivation is a transformation of an entity into another, an update of an entity resulting in a new one, or the construction of a new entity based on a pre-existing entity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasDerivedFrom'} })
    generated_by: Optional[str] = Field(default=None, description="""Generation is the completion of production of a new entity by an activity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasGeneratedBy'} })
    id: str = Field(default=..., description="""A unique identifier for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    name: Optional[str] = Field(default=None, description="""A human-readable name for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    description: Optional[str] = Field(default=None, description="""A human-readable description for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })


class Dataset(Entity):
    """
    A dbGaP dataset (pht accession): a table of variables collected for a study
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dm-bip/mapping-prov-schema'})

    variables: Optional[list[Variable]] = Field(default=None, description="""The dbGaP variables (phv accessions) contained in this dataset""", json_schema_extra = { "linkml_meta": {'domain_of': ['Dataset']} })
    attributed_to: Optional[str] = Field(default=None, description="""Attribution is the ascribing of an entity to an agent""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasAttributedTo'} })
    derived_from: Optional[list[str]] = Field(default=None, description="""A derivation is a transformation of an entity into another, an update of an entity resulting in a new one, or the construction of a new entity based on a pre-existing entity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasDerivedFrom'} })
    generated_by: Optional[str] = Field(default=None, description="""Generation is the completion of production of a new entity by an activity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasGeneratedBy'} })
    id: str = Field(default=..., description="""A unique identifier for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    name: Optional[str] = Field(default=None, description="""A human-readable name for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    description: Optional[str] = Field(default=None, description="""A human-readable description for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })


class Study(Entity):
    """
    A research study (e.g. a dbGaP phs accession): the root grouping for mapping provenance, containing the datasets, transformation specs, and derived entities that belong to it
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dm-bip/mapping-prov-schema',
         'tree_root': True})

    datasets: Optional[list[Dataset]] = Field(default=None, description="""The dbGaP datasets (pht accessions) that contributed data to this study's mappings""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study']} })
    transformation_specs: Optional[list[TransformationSpec]] = Field(default=None, description="""The transformation specs defining this study's mappings""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study']} })
    derived_entities: Optional[list[Entity]] = Field(default=None, description="""Entities produced by applying this study's transformation specs""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study']} })
    attributed_to: Optional[str] = Field(default=None, description="""Attribution is the ascribing of an entity to an agent""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasAttributedTo'} })
    derived_from: Optional[list[str]] = Field(default=None, description="""A derivation is a transformation of an entity into another, an update of an entity resulting in a new one, or the construction of a new entity based on a pre-existing entity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasDerivedFrom'} })
    generated_by: Optional[str] = Field(default=None, description="""Generation is the completion of production of a new entity by an activity""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'slot_uri': 'prov:wasGeneratedBy'} })
    id: str = Field(default=..., description="""A unique identifier for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    name: Optional[str] = Field(default=None, description="""A human-readable name for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })
    description: Optional[str] = Field(default=None, description="""A human-readable description for a thing""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedThing']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
NamedThing.model_rebuild()
Entity.model_rebuild()
File.model_rebuild()
DataObject.model_rebuild()
TransformationSpec.model_rebuild()
Activity.model_rebuild()
Agent.model_rebuild()
Variable.model_rebuild()
Dataset.model_rebuild()
Study.model_rebuild()
