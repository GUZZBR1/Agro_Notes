<?php

declare(strict_types=1);

namespace Drupal\farm_quick;

use Drupal\Core\Cache\CacheBackendInterface;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Plugin\DefaultPluginManager;
use Drupal\farm_quick\Attribute\QuickForm;
use Drupal\farm_quick\Plugin\QuickForm\QuickFormInterface;

/**
 * Quick Form plugin manager.
 */
class QuickFormPluginManager extends DefaultPluginManager {

  public function __construct(
    \Traversable $namespaces,
    CacheBackendInterface $cache_backend,
    ModuleHandlerInterface $module_handler,
  ) {
    parent::__construct(
      'Plugin/QuickForm',
      $namespaces,
      $module_handler,
      QuickFormInterface::class,
      QuickForm::class,
      'Drupal\farm_quick\Annotation\QuickForm'
    );
    $this->alterInfo('quick_form_info');
    $this->setCacheBackend($cache_backend, 'quick_forms');
  }

}
