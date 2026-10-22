<?php

declare(strict_types=1);

namespace Drupal\farm_quick\Routing;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\DependencyInjection\ContainerInjectionInterface;
use Drupal\farm_quick\Form\QuickForm;
use Drupal\farm_quick\QuickFormInstanceManagerInterface;
use Symfony\Component\Routing\Route;
use Symfony\Component\Routing\RouteCollection;

/**
 * Defines quick form routes.
 */
class QuickFormRoutes implements ContainerInjectionInterface {

  use AutowireTrait;

  public function __construct(
    protected QuickFormInstanceManagerInterface $quickFormInstanceManager,
  ) {}

  /**
   * Provides routes for quick forms.
   *
   * @return \Symfony\Component\Routing\RouteCollection
   *   Returns a route collection.
   */
  public function routes(): RouteCollection {
    $route_collection = new RouteCollection();
    /** @var \Drupal\farm_quick\Entity\QuickFormInstanceInterface[] $quick_forms */
    $quick_forms = $this->quickFormInstanceManager->getInstances();
    foreach ($quick_forms as $id => $quick_form) {

      // Skip quick forms that are disabled.
      if (!$quick_form->status()) {
        continue;
      }

      // Build a route for the quick form.
      $route = new Route(
        "/quick/$id",
        [
          '_form' => QuickForm::class,
          '_title_callback' => QuickForm::class . '::getTitle',
          'id' => $id,
        ],
        [
          '_custom_access' => QuickForm::class . '::access',
        ],
      );
      $route_collection->add("farm.quick.$id", $route);
    }
    return $route_collection;
  }

}
