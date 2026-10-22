# Plan Records

A Plan Record in farmOS is a special record that is used to represent a
relationship between a [Plan](/model/type/plan) and another record in farmOS
(eg: an [Asset](/model/type/asset) or [Log](/model/type/log)). They provide a
place to store additional metadata about this relationship, and are typically
used behind the scenes by modules that provide [Plan](/model/type/plan) types
and associated UI features.

## Type

Each Plan Record must have a type. All Plan Record types have a common set of
attributes and relationships. Specific Plan Record types (also called "bundles")
may also add additional attributes and relationships (collectively referred to
as "fields"). Plan Record types are defined by modules, and are only available
if their module is enabled.

*farmOS core does not currently provide any Plan Record types.*

## ID

Each Plan Record will be assigned two unique IDs in the database: a universally
unique identifier (UUID), and an internal numeric ID.

The UUID will be unique **across** farmOS databases. The internal ID will only
be unique to a **single** farmOS database. Therefore, the farmOS API uses UUIDs
to ensure that IDs pulled from multiple farmOS databases do not conflict.
Internally, farmOS modules use the internal IDs to perform CRUD operations.

## Attributes

Plan Records may have attributes that serve to store information about the
relationship between the Plan and the record being referenced.

Plan Records do not have any standard attributes. Modules can add additional
attributes.

## Relationships

All Plan Records have the same standard set of relationships. It is assumed that
modules will add at least one additional relationship to another record (eg:
Asset or Log).

### Standard relationships

Relationships that are common to all Plan Record types include:

- Plan

#### Plan

Every Plan Record must specify a single [Plan](/model/type/plan) that it is
associated with.
