# Fields

## Adding fields

A module may add additional fields to assets, logs, and other entity types in
farmOS.

The following documents how to add fields to existing entity types. See
[Entity types](/development/module/entities) to understand how to create new
asset, log, and plan types with custom fields on them.

### Base fields

If the field should be added to all bundles of a given entity type (eg: all log
types), then they should be added as "base fields" via
`hook_entity_base_field_info()`.

A `farm_field.factory` helper service is provided to make this easier. For more
information on how this works, see [Field factory service](/development/module/services/#field-factory-service).

To get started, place the following in a `src/Hook/FieldHooks.php` file
(replace `mymodule` with the name of your module, and `myfield` with the name
of the new field):

```php
<?php

declare(strict_types=1);

namespace Drupal\mymodule\Hook;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for mymodule.
 */
class FieldHooks {

  use AutowireTrait;
  use StringTranslationTrait;

  public function __construct(
    protected FarmFieldFactoryInterface $farmFieldFactory,
  ) {}

  /**
   * Implements hook_entity_base_field_info().
   */
  #[Hook('entity_base_field_info')]
  public function entityBaseFieldInfo(EntityTypeInterface $entity_type) {
    $fields = [];
    
    // Add a new string base field to log entities.
    if ($entity_type->id() == 'log') {
    
      // Options for the new field. See Field options below.
      $options = [
        'type' => 'string',
        'label' => $this->t('My new field'),
        'description' => $this->t('My field description.'),
        'weight' => [
          'form' => 10,
          'view' => 10,
        ],
      ];
      $fields['myfield'] = \Drupal::service('farm_field.factory')->baseFieldDefinition($options);
    }
    
    return $fields;
  }

}
```

### Bundle fields

If the field should only be added to a single bundle (eg: only "Input" logs),
then they should be added as "bundle fields" via
`hook_farm_entity_bundle_field_info()`&ast;

&ast; Note that this is a custom hook provided  by farmOS, which may be
deprecated in favor of a core Drupal hook in the future. See core issue:
[https://www.drupal.org/node/2346347](https://www.drupal.org/node/2346347)

A `farm_field.factory` helper service is provided to make this easier. For more
information on how this works, see [Field factory service](/development/module/services/#field-factory-service).

The format for bundle field definitions is identical to base field definitions
(above), but the `bundleFieldDefinition()` method must be used instead of
`baseFieldDefinition()`.

To get started, place the following in a `src/Hook/FieldHooks.php` file in your
module (replace `mymodule` with the name of your module, and `myfield` with the
name of the new field):

```php
<?php

declare(strict_types=1);

namespace Drupal\mymodule\Hook;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for mymodule.
 */
class FieldHooks {

  use AutowireTrait;
  use StringTranslationTrait;

  public function __construct(
    protected FarmFieldFactoryInterface $farmFieldFactory,
  ) {}

  /**
   * Implements hook_farm_entity_bundle_field_info().
   */
  #[Hook('farm_entity_bundle_field_info')]
  public function farmEntityBundleFieldInfo(EntityTypeInterface $entity_type, string $bundle) {
    $fields = [];

    // Add a new string bundle field to input logs.
    if ($entity_type->id() == 'log' && $bundle == 'input') {
    
      // Options for the new field. See Field options below.
      $options = [
        'type' => 'string',
        'label' => $this->t('My new field'),
        'description' => $this->t('My field description.'),
        'weight' => [
          'form' => 10,
          'view' => 10,
        ],
      ];
      $fields['myfield'] = \Drupal::service('farm_field.factory')->bundleFieldDefinition($options);
    }

    return $fields;
  }

}
```

### Update hook

The code above will only create new fields when the module is first installed.
If your module is already installed, and you want to add a new base or bundle
field to an entity type, you will need to provide an [update hook](updates) (in
addition to the base/bundle field declaration described above), which instructs
Drupal to install the new field when database updates are run (either via
`/update.php` or `drush updb`). This update hook should be added to a file
called `[module-name].post_update.php` in the root of the module's directory.
The update hook is just a PHP function with a name in the form:
`[module-name]_post_update_[update-name]()`.

For example, the following will install the same `myfield` bundle field declared
in the `mymodule.module` example above:

`mymodule.post_update.php`:

```php
<?php

/**
 * @file
 * Post update hooks for mymodule.
 */

declare(strict_types=1);

/**
 * Add "My new field" to logs.
 */
function mymodule_post_update_add_myfield(&$sandbox) {
  $options = [
    'type' => 'string',
    'label' => t('My new field'),
    'description' => t('My field description.'),
    'weight' => [
      'form' => 10,
      'view' => 10,
    ],
  ];
  $field_definition = \Drupal::service('farm_field.factory')->bundleFieldDefinition($options);
  \Drupal::entityDefinitionUpdateManager()->installFieldStorageDefinition('myfield', 'log', 'mymodule', $field_definition);
}
```

There are a few things to make note of in this example:

1. Always copy the `$options` verbatim from your other hook. Do not try to
   reuse code in this context, because you can't predict when this update hook
   will run. For example, if the end user does not update their modules
   frequently, and the field changes multiple times across versions, it could
   result in unpredictable issues. Update hooks should always be very specific
   about the changes they make, and not rely on external code that may change.
2. You do not need to specify that this field will only be installed on `input`
   logs in this context. The update hook is only responsible for creating the
   necessary database table(s) for the field, but the implementation of
   `hook_farm_entity_bundle_field_info()` is what tells Drupal which bundle(s)
   the field can be used on.
3. This example installs a bundle field. To install a base field, replace
   `->bundleFieldDefinition($options)` with `->baseFieldDefinition($options)`.

### Views and CSV Importers

Bundle fields will automatically be added to farmOS Views provided by the
`farm_ui_views` module, like `/assets` and `/logs`, and to the default
[CSV importers](csv) provided by the `farm_import_csv` module. Base fields,
however, are not automatically added to these. Modules that add base fields must
implement `hook_farm_ui_views_base_fields()` and
`hook_farm_import_csv_base_fields()` in order to tell farmOS to include them.

For example, to add the `myfield` base field declared in the example
`hook_entity_base_field_info()` hook above, the following additional methods can
be added to the same `src/Hook/FieldHooks.php` class:

```php
  /**
   * Implements hook_farm_ui_views_base_fields().
   */
  #[Hook('farm_ui_views_base_fields')]
  public function farmUiViewsBaseFields(string $entity_type) {
    $base_fields = [];

    // Add the myfield base field to farmOS log Views.
    if ($entity_type == 'log') {
      $base_fields[] = 'myfield';
    }

    return $base_fields;
  }
```

```php
  /**
   * Implements hook_farm_import_csv_base_fields().
   */
  #[Hook('farm_import_csv_base_fields')]
  public function farmImportCsvBaseFields(string $entity_type) {
    $base_fields = [];

    // Add the myfield base field to log CSV importers.
    if ($entity_type == 'log') {
      $base_fields[] = 'myfield';
    }

    return $base_fields;
  }
```

## Select options

Certain fields on assets and logs include a list of options to select from.
These include:

- **Flags** (on assets, logs, and plans)
    - Monitor (`monitor`)
    - Needs review (`needs_review`)
    - Priority (`priority`)
- **Land types** (on Land assets)
    - Property (`property`)
    - Field (`field`)
    - Bed (`bed`)
    - Paddock (`paddock`)
    - Landmark (`landmark`)
    - Other (`other`)
- **Structure types** (on Structure assets)
    - Building (`building`)
    - Greenhouse (`greenhouse`)
- **Lab test type** (on Lab test logs)
    - Soil test (`soil`)
    - Water test (`water`)
- **ID tag type** (on assets)
    - Electronic ID (`eid`, on all assets)
    - Other (`other`, on all assets)
    - Brand (`brand`, on Animal assets)
    - Ear tag (`ear_tag`, on Animal assets)
    - Leg band (`leg_band`, on Animal assets)
    - Tattoo (`tattoo`, on Animal assets)

These options are provided as configuration entities by farmOS modules in the
form of YAML files.

Existing options can be overridden or removed by editing/deleting the entities
in the active configuration of the site. (**Warning** changing core types runs
the risk of conflicting with future farmOS updates).

Note that the file name is important and must follow a specific pattern. This
is generally in the form `[select_module_name].[select_field].[id].yml`. See
the examples for more info.

### Examples:

#### Flag

An "Organic" flag can be provided by a module named `my_module` by creating a
file called `farm_flag.flag.organic.yml` in `my_module/config/install`:

```yaml
langcode: en
status: true
dependencies:
  enforced:
    module:
      - my_module
id: organic
label: Organic
entity_types: null
```

Note that the file name is in the form `farm_flag.flag.[id].yml`.

The most important parts are the `id`, which is a unique machine name for
the flag, `label`, which is the human readable/translatable label that will be
shown in the select field and other parts of the UI, and `entity_types`, which
can optionally specify the entity types and bundles that this flag applies to.

The `langcode` and `status` and `dependencies` are standard configuration
entity properties. By putting the module's name in "enforced modules" it will
ensure that the flag is removed when the module is uninstalled.

Flags can be limited to certain entity types and bundles via an optional
`entity_types` property. This accepts a set of entity types with arrays of
bundles that the flag applies to (or `all` to apply to all bundles). For
example, to create a flag that only applies to Animal assets:

```yaml
entity_types:
  asset:
    - animal
```

To create a flag that applies to all asset types and log types, but not plans,
specify `all` for the `asset` and `log` bundles, but omit the `plan` entity
type:

```yaml
entity_types:
  asset:
    - all
  log:
    - all
```

#### Land type

The "Land" module in farmOS provides a "Field" type like this:

`land/config/install/farm_land.land_type.field.yml`

```yaml
langcode: en
status: true
dependencies:
  enforced:
    module:
      - farm_land
id: field
label: Field
```

Note that the file name is in the form `farm_land.land_type.[id].yml`.

#### Structure type

The "Structure" module in farmOS provides a "Building" type like this:

`structure/config/install/farm_structure.structure_type.building.yml`

```yaml
langcode: en
status: true
dependencies:
  enforced:
    module:
      - farm_structure
id: building
label: Building
```

Note that the file name is in the form `farm_structure.structure_type.[id].yml`.

#### Lab test type

The "Lab test" module in farmOS provides a "Soil test" type like this:

`lab_test/config/install/farm_lab_test.lab_test_type.soil.yml`

```yaml
langcode: en
status: true
dependencies:
  enforced:
    module:
      - farm_lab_test
id: soil
label: Soil test
```

Note that the file name is in the form `farm_lab_test.lab_test_type.[id].yml`.

#### ID tag type

ID tag types are similar to Flags, in that they have an `id` and `label`. They
also have an additional `bundle` property, which allows them to be limited to
certain types of assets.

For example, an "Ear tag" type, provided by the "Animal asset" module, only
applies to "Animal" assets:

`animal/config/install/farm_id_tag.id_tag.ear_tag.yml`

```yaml
langcode: en
status: true
dependencies:
  enforced:
    module:
      - farm_animal
      - farm_id_tag
id: ear_tag
label: Ear tag
bundles:
  - animal
```

Note that the file name is in the form `farm_flag.flag.ear_tag.[id].yml`.

If you want the tag type to apply to all assets, set `bundles: null`.
(or can it just be omitted?)
