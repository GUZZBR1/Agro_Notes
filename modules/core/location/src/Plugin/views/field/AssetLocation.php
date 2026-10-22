<?php

declare(strict_types=1);

namespace Drupal\farm_location\Plugin\views\field;

use Drupal\views\Attribute\ViewsField;
use Drupal\views\Plugin\views\field\EntityField;

/**
 * A field that displays asset location.
 *
 * @ingroup views_field_handlers
 */
#[ViewsField("asset_location")]
class AssetLocation extends EntityField {

}
