<?php

declare(strict_types=1);

namespace Drupal\farm_setup;

use Drupal\Core\Cache\CacheBackendInterface;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Plugin\DefaultPluginManager;
use Drupal\farm_setup\Attribute\SetupForm;
use Drupal\farm_setup\Plugin\SetupForm\SetupFormInterface;

/**
 * Setup form plugin manager.
 */
class SetupFormPluginManager extends DefaultPluginManager {

  public function __construct(
    \Traversable $namespaces,
    CacheBackendInterface $cache_backend,
    ModuleHandlerInterface $module_handler,
  ) {
    parent::__construct(
      'Plugin/SetupForm',
      $namespaces,
      $module_handler,
      SetupFormInterface::class,
      SetupForm::class,
    );
    $this->alterInfo('farm_setup_form_info');
    $this->setCacheBackend($cache_backend, 'farm_setup_forms');
  }

  /**
   * {@inheritdoc}
   */
  public function getDefinitions() {

    // Sort definitions by weight.
    $definitions = parent::getDefinitions();
    uasort($definitions, function ($a, $b) {
      return $a['weight'] <=> $b['weight'];
    });
    return $definitions;
  }

}
