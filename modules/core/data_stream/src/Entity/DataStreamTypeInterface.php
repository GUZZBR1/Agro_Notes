<?php

declare(strict_types=1);

namespace Drupal\data_stream\Entity;

use Drupal\Core\Config\Entity\ConfigEntityInterface;
use Drupal\Core\Entity\EntityDescriptionInterface;

/**
 * Provides an interface for defining Data Stream type entities.
 */
interface DataStreamTypeInterface extends ConfigEntityInterface, EntityDescriptionInterface {

}
