<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Plugin\Organization\OrganizationType;

use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\farm_entity\Attribute\OrganizationType;
use Drupal\farm_entity\Plugin\Organization\OrganizationType\FarmOrganizationType;

/**
 * Provides the farm organization type.
 */
#[OrganizationType(
  id: 'farm',
  label: new TranslatableMarkup('Farm'),
)]
class Farm extends FarmOrganizationType {

}
