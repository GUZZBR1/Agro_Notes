<?php

declare(strict_types=1);

namespace Drupal\farm_entity;

use Drupal\Core\Plugin\ContainerFactoryPluginInterface;
use Drupal\Core\Plugin\PluginBase;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Provides a FarmEntityTypeBase for plugins to extends.
 */
abstract class FarmEntityTypeBase extends PluginBase implements ContainerFactoryPluginInterface {

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    protected FarmFieldFactoryInterface $farmFieldFactory,
  ) {
    parent::__construct($configuration, $plugin_id, $plugin_definition);
  }

}
