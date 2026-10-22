<?php

declare(strict_types=1);

namespace Drupal\farm_group\Plugin\views\field;

use Drupal\views\Attribute\ViewsField;
use Drupal\views\Plugin\views\field\EntityField;

/**
 * A field that displays asset group.
 *
 * @ingroup views_field_handlers
 */
#[ViewsField("asset_group")]
class AssetGroup extends EntityField {

}
